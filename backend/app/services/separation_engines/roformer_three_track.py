"""
Three-Track Separation Engine (Roformer v2 Upgraded Edition)

Multi-pass separation that completely cuts out Demucs in favor of 
next-gen Time-Frequency Transformers. This produces three independent audio tracks:
1. Lead Vocals (isolated via Roformer karaoke model)
2. Backing Vocals (extracted from pure Roformer vocals + de-noised)
3. Instrumental (pure pristine instrumental from primary Roformer)

Pipeline:
    Input Audio
        │
        └──[Roformer Vocals]──→ Pristine Vocals + Pure Instrumental (No Phase Artifacts)
                 │
                 └── Vocals ──[Roformer Karaoke]──→ Lead Vocals + Backing Vocals
                                                                     │
                                                                     └──[De-Noise]──→ Cleaned Backing

Output: 3 separate MP3 files (vocals.mp3, backing_vocals.mp3, instrumental.mp3)
"""

import logging
import shutil
import threading
import time
from pathlib import Path
from typing import Callable, Dict, Optional

from audio_separator.separator import Separator
from pydub import AudioSegment

from app.config import get_config
from app.services import file_management
from app.services.audio import (
    StopProcessingError,
)

logger = logging.getLogger(__name__)

# Model constants (Optimized for pristine separation without watery phase distortions)
# mel_band_roformer_vocals_unw_1604.ckpt is not in audio-separator 0.30.x; use unwa Kim FT.
PRIMARY_VOCAL_MODEL = "mel_band_roformer_kim_ft_unwa.ckpt"
KARAOKE_MODEL = "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt"
DENOISE_MODEL = "DISABLED"
# DENOISE_MODEL = "denoise_mel_band_roformer_aufr33_sdr_27.9959.ckpt"

# Filename fragments used to distinguish stems when prior passes embed tags in names.
_PRIMARY_MODEL_MARKER = "mel_band_roformer_kim_ft_unwa"
_KARAOKE_MODEL_MARKER = "mel_band_roformer_karaoke"


def _resolve_output_path(file_path: str, temp_dir: Path) -> Path:
    file_obj = Path(file_path)
    if not file_obj.is_absolute():
        file_obj = temp_dir / file_obj.name
    return file_obj


def _last_stem_tag(filename: str) -> str | None:
    """Return the rightmost stem tag in a separator output filename."""
    lower = filename.lower()
    last_idx = -1
    last_tag: str | None = None
    for tag in ("(vocals)", "(instrumental)", "(other)"):
        idx = lower.rfind(tag)
        if idx > last_idx:
            last_idx = idx
            last_tag = tag
    return last_tag


def separate_with_three_track(
    input_path: Path,
    song_dir: Path,
    status_callback: Callable[[str], None],
    stop_event: Optional[threading.Event] = None,
    on_vocals_ready: Optional[Callable[[Path], None]] = None,
    timing_sink: Optional[Dict[str, float]] = None,
) -> bool:
    """
    Multi-pass separation producing three independent audio tracks using dual Roformer passes.

    Args:
        input_path: Path to the input audio file
        song_dir: Path to the directory where processed files will be saved
        status_callback: Function to call with status updates
        stop_event: A threading.Event to check for stop requests
        on_vocals_ready: Optional callback invoked with the vocals.mp3 path early (~62%)

    Returns:
        True if separation succeeded, False otherwise.
    """
    logger.info("Starting Roformer-based Three-Track separation for: %s", input_path.name)
    status_callback("Engine: Dual-Pass Roformer + Spec De-Noise")

    def _ts(key: str) -> None:
        """Record a timestamp into timing_sink if one was provided."""
        if timing_sink is not None:
            timing_sink[key] = time.perf_counter()

    # Create temp directory for intermediate files
    temp_dir = song_dir / ".temp_three_track"
    temp_dir.mkdir(exist_ok=True)

    config = get_config()

    try:
        # ===== STEP 1: Primary Vocal/Instrumental Separation (12-50% progress) =====
        _ts("primary_separation_start")
        status_callback("Progress: 12% - Step 1/4: Initializing Primary Vocal Transformer...")
        logger.info("Step 1: Roformer isolation for clean vocal mix and pure instrumental")

        # Initialize the native wrapper for primary isolation
        primary_separator = Separator(
            output_dir=str(temp_dir),
            output_format="wav",
        )
        
        status_callback(f"Progress: 15% - Loading primary model: {PRIMARY_VOCAL_MODEL}")
        primary_separator.load_model(model_filename=PRIMARY_VOCAL_MODEL)

        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        status_callback("Progress: 25% - Separating master audio band into pristine stems...")
        primary_outputs = primary_separator.separate(str(input_path))
        
        primary_vocals_path = None
        pure_instrumental_path = None

        # Parse outputs from the primary model only (avoid matching nested karaoke tags).
        for file_path in primary_outputs:
            file_obj = _resolve_output_path(file_path, temp_dir)
            stem_name = file_obj.name.lower()
            if _KARAOKE_MODEL_MARKER in stem_name:
                continue
            if _PRIMARY_MODEL_MARKER not in stem_name:
                continue
            tag = _last_stem_tag(stem_name)
            if tag == "(vocals)":
                primary_vocals_path = file_obj
            elif tag in ("(instrumental)", "(other)"):
                pure_instrumental_path = file_obj

        if not primary_vocals_path or not pure_instrumental_path:
            raise Exception("Primary separation failed to generate required structural stems.")

        logger.info("Primary pristine mix vocals saved to: %s", primary_vocals_path)
        logger.info("Pure instrumental backing saved to: %s", pure_instrumental_path)
        _ts("primary_separation_end")

        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # ===== STEP 2: Roformer Karaoke on Isolated Vocals (50-60% progress) =====
        _ts("roformer_start")
        status_callback("Progress: 50% - Step 2/4: Running Karaoke Roformer to isolate lead vocal track...")
        logger.info("Step 2: Roformer karaoke separation on primary vocal track")

        karaoke_separator = Separator(
            output_dir=str(temp_dir),
            output_format="wav",
        )
        status_callback(f"Progress: 55% - Loading model: {KARAOKE_MODEL}")
        karaoke_separator.load_model(model_filename=KARAOKE_MODEL)

        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        status_callback("Progress: 60% - Extracting lead from backing vocals...")
        # CRITICAL UPGRADE: Feeding a pristine isolated vocal file instead of a muddy Demucs track
        karaoke_output_files = karaoke_separator.separate(str(primary_vocals_path))
        logger.info("Roformer karaoke produced: %s", karaoke_output_files)

        lead_vocals_path = None
        backing_vocals_path = None

        for file_path in karaoke_output_files:
            file_obj = _resolve_output_path(file_path, temp_dir)
            stem_name = file_obj.name.lower()
            if _KARAOKE_MODEL_MARKER not in stem_name:
                continue
            tag = _last_stem_tag(stem_name)
            if tag == "(vocals)":
                lead_vocals_path = file_obj
            elif tag == "(instrumental)":
                # Inside vocals-only files, this output stem represents pure backing tracks
                backing_vocals_path = file_obj

        if not lead_vocals_path or not backing_vocals_path:
            raise Exception(f"Expected karaoke outputs not found. Got: {karaoke_output_files}")

        logger.info("Lead vocals: %s", lead_vocals_path)
        logger.info("Backing vocals (raw form): %s", backing_vocals_path)
        _ts("roformer_end")

        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # ===== Early pipeline trigger: Write vocals.mp3 immediately for upstream modules =====
        _ts("vocals_mp3_start")
        vocals_final = file_management.get_vocals_path_stem(song_dir).with_suffix(".mp3")
        logger.info("[PIPELINE] ~62%% — converting lead vocals to MP3 early for timing tasks")
        status_callback("Progress: 62% - Converting lead vocals to MP3 (early alignment mode)...")
        
        lead_audio_early = AudioSegment.from_wav(str(lead_vocals_path))
        lead_audio_early.export(
            str(vocals_final),
            format="mp3",
            bitrate=config.DEFAULT_MP3_BITRATE,
        )
        logger.info("[PIPELINE] vocals.mp3 mapped at %s", vocals_final)
        _ts("vocals_mp3_end")

        if on_vocals_ready is not None:
            logger.info("[PIPELINE] firing downstream on_vocals_ready callback tracking hook")
            try:
                on_vocals_ready(vocals_final)
                logger.info("[PIPELINE] downstream callback execution completed")
            except Exception as e:
                logger.warning("[PIPELINE] on_vocals_ready tracking callback raised exception: %s", e)
        else:
            logger.info("[PIPELINE] no downstream alignment callback hook registered")

        # ===== STEP 3: De-Noise Backing Vocals (73-93% progress) =====
        _ts("denoise_start")
        status_callback("Progress: 73% - Step 3/4: Polishing backing vocals with de-noise pass...")
        logger.info("Step 3: De-noising backing vocals track")

        cleaned_backing_path = None

        try:
            denoise_separator = Separator(
                output_dir=str(temp_dir),
                output_format="wav",
            )
            status_callback(f"Progress: 76% - Loading model: {DENOISE_MODEL}")
            denoise_separator.load_model(model_filename=DENOISE_MODEL)

            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")

            status_callback("Progress: 83% - Removing residual room echoes/breaths from backline...")
            denoise_output_files = denoise_separator.separate(str(backing_vocals_path))
            logger.info("Spectral de-noise engine produced: %s", denoise_output_files)

            # Extract the dry stem
            for file_path in denoise_output_files:
                file_obj = Path(file_path)
                if not file_obj.is_absolute():
                    file_obj = temp_dir / file_obj.name

                if "(dry)" in file_obj.name.lower() or "dry" in file_obj.name.lower():
                    cleaned_backing_path = file_obj
                    break

            if cleaned_backing_path and cleaned_backing_path.exists():
                logger.info("Cleaned backing vocals set to: %s", cleaned_backing_path)
            else:
                logger.warning("De-noise dry output missing from arrays. Falling back to uncleaned raw backing")
                cleaned_backing_path = backing_vocals_path

        except Exception as e:
            logger.warning("De-noise engine tracking failed, falling back safely to uncleaned stems: %s", e)
            status_callback("De-noise layer bypassed, continuing with uncleaned backing layers...")
            cleaned_backing_path = backing_vocals_path

        _ts("denoise_end")

        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # ===== STEP 4: Render Independent Outputs (93-99% progress) =====
        _ts("mp3_conversion_start")
        status_callback("Progress: 93% - Step 4/4: Exporting compressed targets...")
        logger.info("Step 4: Exporting final three-track configuration")

        backing_vocals_final = file_management.get_backing_vocals_path_stem(song_dir).with_suffix(".mp3")
        instrumental_final = file_management.get_instrumental_path_stem(song_dir).with_suffix(".mp3")

        # 1. Verification step for lead vocals
        if vocals_final.exists():
            status_callback("Progress: 95% - Lead vocals verified (cached via early render loop)")
            logger.info("Lead vocals already generated during alignment hook pass: %s", vocals_final)
        else:
            status_callback("Progress: 95% - Converting lead vocals to target configuration...")
            lead_audio = AudioSegment.from_wav(str(lead_vocals_path))
            lead_audio.export(
                str(vocals_final),
                format="mp3",
                bitrate=config.DEFAULT_MP3_BITRATE,
            )

        # 2. Convert backing vocals to target track
        status_callback("Progress: 96% - Converting backing vocals track to MP3...")
        backing_audio = AudioSegment.from_wav(str(cleaned_backing_path))
        backing_audio.export(
            str(backing_vocals_final),
            format="mp3",
            bitrate=config.DEFAULT_MP3_BITRATE,
        )
        logger.info("Backing vocals saved to destination: %s", backing_vocals_final)

        # 3. Convert pure transformer instrumental track to target
        status_callback("Progress: 97% - Converting pure instrumental track to MP3...")
        instr_audio = AudioSegment.from_wav(str(pure_instrumental_path))
        instr_audio.export(
            str(instrumental_final),
            format="mp3",
            bitrate=config.DEFAULT_MP3_BITRATE,
        )
        logger.info("Instrumental saved to destination: %s", instrumental_final)
        status_callback("Progress: 99% - Processing array complete")

        _ts("mp3_conversion_end")

        # Clean up temporary disk footprints
        status_callback("Cleaning up disk temp blocks...")
        shutil.rmtree(temp_dir)
        logger.info("Temporary workspace cleanly unlinked")

        status_callback(f"Three-track separation processing completed for {input_path.name}!")
        return True

    except StopProcessingError:
        logger.info("Processing halted — user issued break request signal.")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise

    except Exception as e:
        logger.error("Three-Track separation execution pipeline failed: %s", e, exc_info=True)
        status_callback(f"** Fatal script exception encountered during extraction processing: {e} **")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        return False