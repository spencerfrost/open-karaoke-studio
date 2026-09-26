"""
Clean Backing Vocals Separation Engine

Multi-pass separation that produces cleaner backing vocals by:
1. Using Demucs for clean instrumental (no artifacts)
2. Using Roformer karaoke model for lead vocal isolation
3. Extracting backing vocals by subtraction
4. Running de-noise pass on backing vocals to remove "watery/metallic" artifacts
5. Merging cleaned backing with clean instrumental

Pipeline:
    Input Audio
        │
        ├──[Demucs htdemucs_ft]──→ Clean Instrumental
        │
        ├──[Roformer Karaoke]──→ Lead Vocals + (Instrumental+Backing)
        │                              │
        │                              └──→ Backing = Roformer_Instr - Demucs_Instr
        │
        └──[De-Noise Model]──→ Cleaned Backing Vocals
                                       │
                                       └──→ Final = Demucs_Instr + Cleaned_Backing

Pros: Cleanest backing vocals, leverages strengths of each model
Cons: Longest processing time (3 model passes)
"""

import logging
import shutil
import threading
from pathlib import Path
from typing import Callable, Optional, Tuple

import librosa
import numpy as np
import soundfile as sf
import torch
from audio_separator.separator import Separator
from demucs.api import Separator as DemucsSeparator
from pydub import AudioSegment

from app.config import get_config
from app.services import file_management
from app.services.audio import (
    create_audio_progress_mapper,
    StopProcessingError,
    make_progress_callback,
    select_device_and_log,
)

logger = logging.getLogger(__name__)

# Model constants
KARAOKE_MODEL = "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt"
DENOISE_MODEL = "denoise_mel_band_roformer_aufr33_sdr_27.9959.ckpt"


def separate_with_clean_backing(
    input_path: Path,
    song_dir: Path,
    status_callback: Callable[[str], None],
    stop_event: Optional[threading.Event] = None,
) -> bool:
    """
    Multi-pass separation with de-noised backing vocals.

    This engine produces:
    - vocals.mp3: Lead vocals only (clean, from Roformer karaoke model)
    - instrumental.mp3: Clean instrumental + de-noised backing vocals

    Args:
        input_path: Path to the input audio file
        song_dir: Path to the directory where processed files will be saved
        status_callback: Function to call with status updates
        stop_event: A threading.Event to check for stop requests

    Returns:
        True if separation succeeded, False otherwise.
    """
    logger.info("Starting Clean Backing separation for: %s", input_path.name)
    status_callback("Engine: Clean Backing (Demucs + Roformer + De-Noise)")

    # Create temp directory for intermediate files
    temp_dir = song_dir / ".temp_clean_backing"
    temp_dir.mkdir(exist_ok=True)

    config = get_config()

    try:
        # ===== STEP 1: Demucs Separation for Clean Instrumental (35-50% progress) =====
        status_callback("Progress: 35% - Step 1/5: Running Demucs for clean instrumental...")
        logger.info("Step 1: Demucs separation")

        device = select_device_and_log(status_callback)

        # Create a wrapped progress callback that maps Demucs [0-100%] to job [35-50%]
        demucs_progress_callback = create_audio_progress_mapper(
            engine_type='demucs',
            base_start=35,
            base_end=50,
            update_fn=lambda prog, msg: status_callback(f"Step 1/5 (Demucs): {msg} [{prog}%]")
        )

        demucs_separator = DemucsSeparator(
            model=config.DEFAULT_MODEL,
            device=device,
            callback=make_progress_callback(demucs_progress_callback, stop_event),
        )

        origin_wave, separated = demucs_separator.separate_audio_file(input_path)

        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # Calculate Demucs instrumental (all non-vocal stems)
        instrumental_stems = [s_name for s_name in separated if s_name != "vocals"]
        if not instrumental_stems:
            raise Exception("No non-vocal stems found in Demucs output")

        demucs_instrumental = torch.zeros_like(separated[instrumental_stems[0]])
        for stem_name in instrumental_stems:
            demucs_instrumental += separated[stem_name]

        # Save Demucs instrumental to temp
        demucs_instr_path = temp_dir / "demucs_instrumental.wav"
        demucs_instr_numpy = demucs_instrumental.cpu().numpy().T
        sf.write(
            str(demucs_instr_path),
            demucs_instr_numpy,
            demucs_separator.samplerate,
            subtype="PCM_16",
        )
        logger.info("Demucs instrumental saved to: %s", demucs_instr_path)

        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # ===== STEP 2: Roformer Karaoke Separation (50-60% progress) =====
        status_callback("Progress: 50% - Step 2/5: Running Roformer for lead vocal isolation...")
        logger.info("Step 2: Roformer karaoke separation")

        karaoke_separator = Separator(
            output_dir=str(temp_dir),
            output_format="wav",
        )
        status_callback(f"Progress: 55% - Loading model: {KARAOKE_MODEL}")
        karaoke_separator.load_model(model_filename=KARAOKE_MODEL)

        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        status_callback("Progress: 60% - Separating with Roformer karaoke model...")
        karaoke_output_files = karaoke_separator.separate(str(input_path))
        logger.info("Roformer karaoke produced: %s", karaoke_output_files)

        # Find lead vocals and roformer instrumental
        lead_vocals_path = None
        roformer_instr_path = None

        for file_path in karaoke_output_files:
            file_obj = Path(file_path)
            if not file_obj.is_absolute():
                file_obj = temp_dir / file_obj.name

            if "(Vocals)" in file_obj.name:
                lead_vocals_path = file_obj
            elif "(Instrumental)" in file_obj.name:
                roformer_instr_path = file_obj

        if not lead_vocals_path or not roformer_instr_path:
            raise Exception(
                f"Expected karaoke output files not found. Got: {karaoke_output_files}"
            )

        logger.info("Lead vocals: %s", lead_vocals_path)
        logger.info("Roformer instrumental: %s", roformer_instr_path)

        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # ===== STEP 3: Extract Backing Vocals (60-68% progress) =====
        status_callback("Progress: 60% - Step 3/5: Extracting backing vocals...")
        logger.info("Step 3: Extracting backing vocals by subtraction")

        # Load both instrumentals
        status_callback("Progress: 64% - Loading instrumental tracks...")
        demucs_audio, sr_demucs = librosa.load(
            str(demucs_instr_path), sr=None, mono=False
        )
        roformer_audio, sr_roformer = librosa.load(
            str(roformer_instr_path), sr=None, mono=False
        )

        # Ensure same sample rate
        if sr_demucs != sr_roformer:
            roformer_audio = librosa.resample(
                roformer_audio, orig_sr=sr_roformer, target_sr=sr_demucs
            )
            sr_roformer = sr_demucs

        # Ensure same length (pad shorter one with zeros)
        if demucs_audio.shape[-1] != roformer_audio.shape[-1]:
            max_len = max(demucs_audio.shape[-1], roformer_audio.shape[-1])
            if demucs_audio.shape[-1] < max_len:
                pad_width = (
                    [(0, 0)] * (demucs_audio.ndim - 1)
                    + [(0, max_len - demucs_audio.shape[-1])]
                )
                demucs_audio = np.pad(demucs_audio, pad_width, mode="constant")
            if roformer_audio.shape[-1] < max_len:
                pad_width = (
                    [(0, 0)] * (roformer_audio.ndim - 1)
                    + [(0, max_len - roformer_audio.shape[-1])]
                )
                roformer_audio = np.pad(roformer_audio, pad_width, mode="constant")

        # Extract backing vocals: roformer_instrumental - demucs_instrumental
        # The roformer instrumental contains backing vocals, demucs doesn't
        backing_vocals = roformer_audio - demucs_audio

        # Normalize to prevent clipping
        max_val = np.max(np.abs(backing_vocals))
        if max_val > 0.95:
            backing_vocals = backing_vocals * (0.95 / max_val)

        # Save backing vocals for de-noise processing
        backing_path = temp_dir / "backing_vocals.wav"
        sf.write(str(backing_path), backing_vocals.T, sr_demucs)
        logger.info("Backing vocals extracted to: %s", backing_path)
        status_callback("Progress: 68% - Backing vocals extracted")

        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # ===== STEP 4: De-Noise Backing Vocals (68-78% progress) =====
        status_callback("Progress: 68% - Step 4/5: Cleaning backing vocals with de-noise model...")
        logger.info("Step 4: De-noising backing vocals")

        cleaned_backing_path = None

        try:
            denoise_separator = Separator(
                output_dir=str(temp_dir),
                output_format="wav",
            )
            status_callback(f"Progress: 73% - Loading model: {DENOISE_MODEL}")
            denoise_separator.load_model(model_filename=DENOISE_MODEL)

            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")

            status_callback("Progress: 78% - Running de-noise on backing vocals...")
            denoise_output_files = denoise_separator.separate(str(backing_path))
            logger.info("De-noise produced: %s", denoise_output_files)

            # Find the "dry" (cleaned) stem
            for file_path in denoise_output_files:
                file_obj = Path(file_path)
                if not file_obj.is_absolute():
                    file_obj = temp_dir / file_obj.name

                # De-noise model outputs "dry" stem as the cleaned audio
                if "(dry)" in file_obj.name.lower() or "dry" in file_obj.name.lower():
                    cleaned_backing_path = file_obj
                    break

            if cleaned_backing_path and cleaned_backing_path.exists():
                logger.info("Cleaned backing vocals: %s", cleaned_backing_path)
            else:
                logger.warning(
                    "De-noise dry stem not found, using original backing vocals"
                )
                cleaned_backing_path = backing_path

        except Exception as e:
            # Graceful fallback: use uncleaned backing if de-noise fails
            logger.warning("De-noise failed, using original backing: %s", e)
            status_callback("De-noise model unavailable, using original backing...")
            cleaned_backing_path = backing_path

        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # ===== STEP 5: Create Final Outputs (78-85% progress) =====
        status_callback("Progress: 78% - Step 5/5: Creating final outputs...")
        logger.info("Step 5: Merging and finalizing")

        # Load cleaned backing
        cleaned_backing, sr_cleaned = librosa.load(
            str(cleaned_backing_path), sr=None, mono=False
        )

        # Ensure same sample rate as demucs instrumental
        if sr_cleaned != sr_demucs:
            cleaned_backing = librosa.resample(
                cleaned_backing, orig_sr=sr_cleaned, target_sr=sr_demucs
            )

        # Ensure same length
        if cleaned_backing.shape[-1] != demucs_audio.shape[-1]:
            target_len = demucs_audio.shape[-1]
            if cleaned_backing.shape[-1] < target_len:
                pad_width = (
                    [(0, 0)] * (cleaned_backing.ndim - 1)
                    + [(0, target_len - cleaned_backing.shape[-1])]
                )
                cleaned_backing = np.pad(cleaned_backing, pad_width, mode="constant")
            else:
                cleaned_backing = cleaned_backing[..., :target_len]

        # Mix: Demucs instrumental + cleaned backing vocals
        final_instrumental = demucs_audio + cleaned_backing

        # Normalize to prevent clipping
        max_val = np.max(np.abs(final_instrumental))
        if max_val > 0.95:
            final_instrumental = final_instrumental * (0.95 / max_val)

        # Save final instrumental as WAV first
        final_instr_wav = temp_dir / "final_instrumental.wav"
        sf.write(str(final_instr_wav), final_instrumental.T, sr_demucs)
        logger.info("Final instrumental WAV saved to: %s", final_instr_wav)

        # Convert to MP3 and save to final locations
        vocals_final = file_management.get_vocals_path_stem(song_dir).with_suffix(
            ".mp3"
        )
        instrumental_final = file_management.get_instrumental_path_stem(
            song_dir
        ).with_suffix(".mp3")

        # Convert lead vocals (from Roformer)
        status_callback("Progress: 80% - Converting vocals to MP3...")
        lead_audio = AudioSegment.from_wav(str(lead_vocals_path))
        lead_audio.export(
            str(vocals_final),
            format="mp3",
            bitrate=config.DEFAULT_MP3_BITRATE,
        )
        logger.info("Final vocals saved to: %s", vocals_final)

        # Convert final instrumental
        status_callback("Progress: 82% - Converting instrumental to MP3...")
        instr_audio = AudioSegment.from_wav(str(final_instr_wav))
        instr_audio.export(
            str(instrumental_final),
            format="mp3",
            bitrate=config.DEFAULT_MP3_BITRATE,
        )
        logger.info("Final instrumental saved to: %s", instrumental_final)
        status_callback("Progress: 85% - Step 5/5 complete")

        # Clean up temp directory
        status_callback("Cleaning up temporary files...")
        shutil.rmtree(temp_dir)
        logger.info("Temporary files cleaned up")

        status_callback(f"Clean backing separation complete for {input_path.name}!")
        logger.info("Clean Backing separation completed successfully")

        return True

    except StopProcessingError:
        # User cancelled - clean up and re-raise
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise

    except Exception as e:
        logger.error("Clean Backing separation failed: %s", e, exc_info=True)
        status_callback(f"** Error during Clean Backing separation: {e} **")

        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

        return False
