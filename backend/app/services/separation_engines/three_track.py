"""
Three-Track Separation Engine

Multi-pass separation that produces three independent audio tracks:
1. Lead Vocals (isolated via Roformer karaoke model)
2. Backing Vocals (extracted from Demucs vocals + de-noised)
3. Instrumental (pure instrumental from Demucs, no vocals)

Pipeline:
    Input Audio
        │
        └──[Demucs htdemucs_ft]──→ Vocals (lead+backing) + Pure Instrumental
                    │
                    └── Vocals ──[Roformer Karaoke]──→ Lead Vocals + Backing Vocals
                                                                        │
                                                                        └──[De-Noise]──→ Cleaned Backing

    Output: 3 separate MP3 files (vocals.mp3, backing_vocals.mp3, instrumental.mp3)

Key advantage: Roformer operates on vocals-only audio, eliminating instrumental bleed-through
that occurs when using subtraction methods.
"""

import logging
import shutil
import threading
from pathlib import Path
from typing import Callable, Optional, Tuple

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
        # ===== STEP 1: Demucs Separation (35-50% progress) =====
        status_callback("Progress: 35% - Step 1/4: Running Demucs separation...")
        logger.info("Step 1: Demucs separation for vocals and instrumental")

        device = select_device_and_log(status_callback)

        demucs_progress_callback = create_audio_progress_mapper(
            engine_type="demucs",
            base_start=35,
            base_end=50,
            update_fn=lambda prog, msg: status_callback(
                f"Step 1/4 (Demucs): {msg} [{prog}%]"
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

        # Extract vocals and instrumental from Demucs
        if "vocals" not in separated:
            raise Exception("Vocals stem not found in Demucs output")

        demucs_vocals = separated["vocals"]

        # Calculate Demucs instrumental (all non-vocal stems)
        instrumental_stems = [s_name for s_name in separated if s_name != "vocals"]
        if not instrumental_stems:
            raise Exception("No non-vocal stems found in Demucs output")

        demucs_instrumental = torch.zeros_like(separated[instrumental_stems[0]])
        for stem_name in instrumental_stems:
            demucs_instrumental += separated[stem_name]

        # Save Demucs vocals to temp (input for Roformer)
        demucs_vocals_path = temp_dir / "demucs_vocals.wav"
        demucs_vocals_numpy = demucs_vocals.cpu().numpy().T
        sf.write(
            str(demucs_vocals_path),
            demucs_vocals_numpy,
            demucs_separator.samplerate,
            subtype="PCM_16",
        )
        logger.info("Demucs vocals saved to: %s", demucs_vocals_path)

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

        # ===== STEP 2: Roformer Karaoke on Demucs Vocals (50-60% progress) =====
        status_callback(
            "Progress: 50% - Step 2/4: Running Roformer to separate lead from backing vocals..."
        )
        logger.info("Step 2: Roformer karaoke separation on Demucs vocals")

        karaoke_separator = Separator(
            output_dir=str(temp_dir),
            output_format="wav",
        )
        status_callback(f"Progress: 55% - Loading model: {KARAOKE_MODEL}")
        karaoke_separator.load_model(model_filename=KARAOKE_MODEL)

        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        status_callback("Progress: 60% - Separating lead and backing vocals...")
        karaoke_output_files = karaoke_separator.separate(str(demucs_vocals_path))
        logger.info("Roformer karaoke produced: %s", karaoke_output_files)

        # Find lead vocals and backing vocals
        # When Roformer karaoke processes vocals-only audio:
        # - "Vocals" output = lead vocals
        # - "Instrumental" output = backing vocals (no instruments since input was vocals-only)
        lead_vocals_path = None
        backing_vocals_path = None

        for file_path in karaoke_output_files:
            file_obj = Path(file_path)
            if not file_obj.is_absolute():
                file_obj = temp_dir / file_obj.name

            if "(Vocals)" in file_obj.name:
                lead_vocals_path = file_obj
            elif "(Instrumental)" in file_obj.name:
                # This is actually backing vocals since we fed it vocals-only audio
                backing_vocals_path = file_obj

        if not lead_vocals_path or not backing_vocals_path:
            raise Exception(
                f"Expected karaoke output files not found. Got: {karaoke_output_files}"
            )

        logger.info("Lead vocals: %s", lead_vocals_path)
        logger.info("Backing vocals (raw): %s", backing_vocals_path)

        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # ===== STEP 3: De-Noise Backing Vocals (60-75% progress) =====
        status_callback(
            "Progress: 60% - Step 3/4: Cleaning backing vocals with de-noise model..."
        )
        logger.info("Step 3: De-noising backing vocals")

        cleaned_backing_path = None

        try:
            denoise_separator = Separator(
                output_dir=str(temp_dir),
                output_format="wav",
            )
            status_callback(f"Progress: 65% - Loading model: {DENOISE_MODEL}")
            denoise_separator.load_model(model_filename=DENOISE_MODEL)

            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")

            status_callback("Progress: 70% - Running de-noise on backing vocals...")
            denoise_output_files = denoise_separator.separate(str(backing_vocals_path))
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
                cleaned_backing_path = backing_vocals_path

        except Exception as e:
            # Graceful fallback: use uncleaned backing if de-noise fails
            logger.warning("De-noise failed, using original backing: %s", e)
            status_callback("De-noise model unavailable, using original backing...")
            cleaned_backing_path = backing_vocals_path

        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # ===== STEP 4: Save Three Independent Tracks (75-85% progress) =====
        status_callback("Progress: 75% - Step 4/4: Saving three tracks...")
        logger.info("Step 4: Saving three independent tracks")

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
        status_callback("Progress: 77% - Converting lead vocals to MP3...")
        lead_audio = AudioSegment.from_wav(str(lead_vocals_path))
        lead_audio.export(
            str(vocals_final),
            format="mp3",
            bitrate=config.DEFAULT_MP3_BITRATE,
        )
        logger.info("Lead vocals saved to: %s", vocals_final)

        # 2. Convert cleaned backing vocals to MP3
        status_callback("Progress: 80% - Converting backing vocals to MP3...")
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
        status_callback("Progress: 85% - Step 4/4 complete")

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
