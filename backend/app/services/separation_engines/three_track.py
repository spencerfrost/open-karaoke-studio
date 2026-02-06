"""
Three-Track Separation Engine

Multi-pass separation that produces three independent audio tracks:
1. Lead Vocals (isolated via Roformer karaoke model)
2. Backing Vocals (extracted by subtraction + de-noised)
3. Instrumental (pure instrumental from Demucs, no vocals)

Pipeline:
    Input Audio
        │
        ├──[Demucs htdemucs_ft]──→ Pure Instrumental (bass + drums + other)
        │
        ├──[Roformer Karaoke]──→ Lead Vocals + (Instrumental+Backing)
        │                              │
        │                              └──→ Backing = Roformer_Instr - Demucs_Instr
        │
        └──[De-Noise Model]──→ Cleaned Backing Vocals

    Output: 3 separate MP3 files (vocals.mp3, backing_vocals.mp3, instrumental.mp3)

Based on the clean_backing engine but saves all three tracks independently
instead of merging backing vocals into the instrumental.
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
    StopProcessingError,
    create_audio_progress_mapper,
    detect_bpm,
    make_progress_callback,
    select_device_and_log,
)

logger = logging.getLogger(__name__)

# Model constants
KARAOKE_MODEL = "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt"
DENOISE_MODEL = "denoise_mel_band_roformer_aufr33_sdr_27.9959.ckpt"


def separate_with_three_track(
    input_path: Path,
    song_dir: Path,
    status_callback: Callable[[str], None],
    stop_event: Optional[threading.Event] = None,
) -> Tuple[bool, Optional[float]]:
    """
    Multi-pass separation producing three independent audio tracks.

    This engine produces:
    - vocals.mp3: Lead vocals only (from Roformer karaoke model)
    - backing_vocals.mp3: Cleaned backing vocals (extracted + de-noised)
    - instrumental.mp3: Pure instrumental (Demucs: bass + drums + other)

    Args:
        input_path: Path to the input audio file
        song_dir: Path to the directory where processed files will be saved
        status_callback: Function to call with status updates
        stop_event: A threading.Event to check for stop requests

    Returns:
        Tuple of (success: bool, bpm: Optional[float])
    """
    logger.info("Starting Three-Track separation for: %s", input_path.name)
    status_callback("Engine: Three-Track (Demucs + Roformer + De-Noise)")

    # Create temp directory for intermediate files
    temp_dir = song_dir / ".temp_three_track"
    temp_dir.mkdir(exist_ok=True)

    config = get_config()

    try:
        # ===== STEP 1: Demucs Separation for Pure Instrumental (35-50% progress) =====
        status_callback("Progress: 35% - Step 1/5: Running Demucs for pure instrumental...")
        logger.info("Step 1: Demucs separation")

        device = select_device_and_log(status_callback)

        demucs_progress_callback = create_audio_progress_mapper(
            engine_type="demucs",
            base_start=35,
            base_end=50,
            update_fn=lambda prog, msg: status_callback(
                f"Step 1/5 (Demucs): {msg} [{prog}%]"
            ),
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
        status_callback(
            "Progress: 50% - Step 2/5: Running Roformer for lead vocal isolation..."
        )
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
                pad_width = [(0, 0)] * (demucs_audio.ndim - 1) + [
                    (0, max_len - demucs_audio.shape[-1])
                ]
                demucs_audio = np.pad(demucs_audio, pad_width, mode="constant")
            if roformer_audio.shape[-1] < max_len:
                pad_width = [(0, 0)] * (roformer_audio.ndim - 1) + [
                    (0, max_len - roformer_audio.shape[-1])
                ]
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
        status_callback(
            "Progress: 68% - Step 4/5: Cleaning backing vocals with de-noise model..."
        )
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

        # ===== STEP 5: Save Three Independent Tracks (78-85% progress) =====
        status_callback("Progress: 78% - Step 5/5: Saving three tracks...")
        logger.info("Step 5: Saving three independent tracks")

        vocals_final = file_management.get_vocals_path_stem(song_dir).with_suffix(
            ".mp3"
        )
        backing_vocals_final = file_management.get_backing_vocals_path_stem(
            song_dir
        ).with_suffix(".mp3")
        instrumental_final = file_management.get_instrumental_path_stem(
            song_dir
        ).with_suffix(".mp3")

        # 1. Convert lead vocals (from Roformer) to MP3
        status_callback("Progress: 79% - Converting lead vocals to MP3...")
        lead_audio = AudioSegment.from_wav(str(lead_vocals_path))
        lead_audio.export(
            str(vocals_final),
            format="mp3",
            bitrate=config.DEFAULT_MP3_BITRATE,
        )
        logger.info("Lead vocals saved to: %s", vocals_final)

        # 2. Convert cleaned backing vocals to MP3
        status_callback("Progress: 81% - Converting backing vocals to MP3...")
        backing_audio = AudioSegment.from_wav(str(cleaned_backing_path))
        backing_audio.export(
            str(backing_vocals_final),
            format="mp3",
            bitrate=config.DEFAULT_MP3_BITRATE,
        )
        logger.info("Backing vocals saved to: %s", backing_vocals_final)

        # 3. Convert pure Demucs instrumental to MP3
        status_callback("Progress: 83% - Converting instrumental to MP3...")
        instr_audio = AudioSegment.from_wav(str(demucs_instr_path))
        instr_audio.export(
            str(instrumental_final),
            format="mp3",
            bitrate=config.DEFAULT_MP3_BITRATE,
        )
        logger.info("Instrumental saved to: %s", instrumental_final)
        status_callback("Progress: 85% - Step 5/5 complete")

        # Detect BPM from original audio
        detected_bpm = detect_bpm(input_path, status_callback)

        # Clean up temp directory
        status_callback("Cleaning up temporary files...")
        shutil.rmtree(temp_dir)
        logger.info("Temporary files cleaned up")

        status_callback(f"Three-track separation complete for {input_path.name}!")
        logger.info("Three-Track separation completed successfully")

        return True, detected_bpm

    except StopProcessingError:
        # User cancelled - clean up and re-raise
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise

    except Exception as e:
        logger.error("Three-Track separation failed: %s", e, exc_info=True)
        status_callback(f"** Error during Three-Track separation: {e} **")

        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

        return False, None
