"""
Three-Track Separation Engine

Multi-pass separation that produces three independent audio tracks:
1. Lead Vocals (isolated via Roformer karaoke model)
2. Backing Vocals (extracted from Demucs vocals + de-noised)
3. Instrumental (input mix minus the Demucs vocals)

Pipeline:
    Input Audio
        │
        └──[Demucs htdemucs_ft vocals model]──→ Vocals (lead+backing); Instrumental = mix − vocals
                    │
                    └── Vocals ──[Roformer Karaoke]──→ Lead Vocals + Backing Vocals
                                                                        │
                                                                        └──[De-Noise]──→ Cleaned Backing

    Output: 3 separate MP3 files (vocals.mp3, backing_vocals.mp3, instrumental.mp3)

Key advantage: Roformer operates on vocals-only audio, eliminating instrumental bleed-through
that occurs when using subtraction methods.
"""

import contextlib
import logging
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import soundfile as sf
import torch
from demucs.api import Separator as DemucsSeparator
from pydub import AudioSegment

from app.config import get_config
from app.services import file_management
from app.services.audio import (
    StopProcessingError,
    create_audio_progress_mapper,
    make_progress_callback,
    select_device_and_log,
)

from .roformer_loader import load_separator, release_gpu_memory

logger = logging.getLogger(__name__)

# Model constants
KARAOKE_MODEL = "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt"
DENOISE_MODEL = "denoise_mel_band_roformer_aufr33_sdr_27.9959.ckpt"
# Demucs default is 0.25; 0.1 recomputes less and sounds the same (listened
# 2026-10-10), while 0 leaves faintly audible seams between 7.8 s segments
DEMUCS_OVERLAP = 0.1


def separate_with_three_track(
    input_path: Path,
    song_dir: Path,
    status_callback: Callable[[str], None],
    stop_event: Optional[threading.Event] = None,
    on_vocals_ready: Optional[Callable[[Path], None]] = None,
    timing_sink: Optional[Dict[str, float]] = None,
    karaoke_model: str = KARAOKE_MODEL,
    engine_label: str = "Three-Track (Demucs + Roformer + De-Noise)",
) -> bool:
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
        on_vocals_ready: Optional callback invoked with the vocals.mp3 path as
            soon as lead vocals are converted, while de-noise runs. Called from
            the MP3 encoder thread. Use to dispatch downstream tasks (vocal
            range, lyrics alignment) as early as possible.

    Returns:
        True if separation succeeded, False otherwise.
    """
    logger.info(
        "Starting Three-Track separation for: %s (karaoke model: %s)",
        input_path.name,
        karaoke_model,
    )
    status_callback(f"Engine: {engine_label}")

    def _ts(key: str) -> None:
        """Record a timestamp into timing_sink if one was provided."""
        if timing_sink is not None:
            timing_sink[key] = time.perf_counter()

    # Create temp directory for intermediate files
    temp_dir = song_dir / ".temp_three_track"
    temp_dir.mkdir(exist_ok=True)

    config = get_config()
    bitrate = config.DEFAULT_MP3_BITRATE
    vocals_final = file_management.get_vocals_path_stem(song_dir).with_suffix(".mp3")
    backing_vocals_final = file_management.get_backing_vocals_path_stem(
        song_dir
    ).with_suffix(".mp3")
    instrumental_final = file_management.get_instrumental_path_stem(
        song_dir
    ).with_suffix(".mp3")

    try:
        # Each MP3 is encoded on the CPU as soon as its stem is ready, while the
        # GPU stages run. Leaving the block waits for running exports, so the
        # temp dir is never removed under one.
        with ThreadPoolExecutor(max_workers=3, thread_name_prefix="mp3") as encoder:
            # ===== STEP 1: Demucs Separation (12-50% progress) =====
            _ts("demucs_start")
            status_callback("Progress: 12% - Step 1/4: Running Demucs separation...")
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
                overlap=DEMUCS_OVERLAP,
                callback=make_progress_callback(demucs_progress_callback, stop_event),
            )
            vocals_only = _use_vocals_specialist(demucs_separator)

            with _demucs_autocast(device, config.SEPARATION_USE_AUTOCAST):
                origin_wave, separated = demucs_separator.separate_audio_file(
                    input_path
                )

            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")

            # Extract vocals and instrumental from Demucs
            if "vocals" not in separated:
                raise Exception("Vocals stem not found in Demucs output")

            demucs_vocals = separated["vocals"]

            if vocals_only:
                # The specialist's other stems are poor; the mix minus its vocals
                # sounds the same as the bag's drums + bass + other (listened 2026-10-10)
                demucs_instrumental = origin_wave.cpu() - demucs_vocals.cpu()
            else:
                # Calculate Demucs instrumental (all non-vocal stems)
                instrumental_stems = [s for s in separated if s != "vocals"]
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
            del (
                demucs_separator,
                origin_wave,
                separated,
                demucs_vocals,
                demucs_instrumental,
            )
            release_gpu_memory()
            instrumental_mp3 = encoder.submit(
                _export_mp3, demucs_instr_path, instrumental_final, bitrate
            )
            _ts("demucs_end")

            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")

            # ===== STEP 2: Roformer Karaoke on Demucs Vocals (50-60% progress) =====
            _ts("roformer_start")
            status_callback(
                "Progress: 50% - Step 2/4: Running Roformer to separate lead from backing vocals..."
            )
            logger.info("Step 2: Roformer karaoke separation on Demucs vocals")

            status_callback(f"Progress: 55% - Loading model: {karaoke_model}")
            karaoke_separator = load_separator(karaoke_model, str(temp_dir))

            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")

            status_callback("Progress: 60% - Separating lead and backing vocals...")
            karaoke_output_files = karaoke_separator.separate(str(demucs_vocals_path))
            logger.info("Roformer karaoke produced: %s", karaoke_output_files)
            del karaoke_separator
            release_gpu_memory()

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
            _ts("roformer_end")

            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")

            # Encode lead vocals while de-noise runs; downstream tasks (vocal range,
            # lyrics alignment) are dispatched as soon as vocals.mp3 exists
            status_callback("Progress: 62% - Converting lead vocals to MP3...")
            vocals_mp3 = encoder.submit(
                _export_lead_vocals,
                lead_vocals_path,
                vocals_final,
                bitrate,
                on_vocals_ready,
                stop_event,
            )

            # ===== STEP 3: De-Noise Backing Vocals (73-93% progress) =====
            _ts("denoise_start")
            if config.THREE_TRACK_DENOISE:
                status_callback(
                    "Progress: 73% - Step 3/4: Cleaning backing vocals with de-noise model..."
                )
                logger.info("Step 3: De-noising backing vocals")
                cleaned_backing_path = _denoise_backing(
                    backing_vocals_path, temp_dir, status_callback, stop_event
                )
            else:
                logger.info("Step 3: De-noise disabled, using raw backing vocals")
                cleaned_backing_path = backing_vocals_path
            _ts("denoise_end")

            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")

            # ===== STEP 4: Save Three Independent Tracks (93-99% progress) =====
            _ts("mp3_conversion_start")
            status_callback(
                "Progress: 93% - Step 4/4: Converting backing vocals to MP3..."
            )
            logger.info("Step 4: Saving three independent tracks")
            _export_mp3(cleaned_backing_path, backing_vocals_final, bitrate)
            logger.info("Backing vocals saved to: %s", backing_vocals_final)

            status_callback(
                "Progress: 97% - Finishing lead vocal and instrumental MP3s..."
            )
            vocals_mp3.result()
            instrumental_mp3.result()
            logger.info("Lead vocals and instrumental saved")
            status_callback("Progress: 99% - Step 4/4 complete")

            _ts("mp3_conversion_end")

        # Clean up temp directory
        status_callback("Cleaning up temporary files...")
        shutil.rmtree(temp_dir)
        logger.info("Temporary files cleaned up")

        status_callback(f"Three-track separation complete for {input_path.name}!")
        logger.info("Three-Track separation completed successfully")

        return True

    except (StopProcessingError, torch.cuda.OutOfMemoryError):
        # Cancellation and a full GPU are the job's to handle (cancel / retry
        # later) - clean up and re-raise
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise

    except Exception as e:
        logger.error("Three-Track separation failed: %s", e, exc_info=True)
        status_callback(f"** Error during Three-Track separation: {e} **")

        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

        return False


def _export_mp3(wav_path: Path, mp3_path: Path, bitrate: str) -> None:
    AudioSegment.from_wav(str(wav_path)).export(
        str(mp3_path), format="mp3", bitrate=bitrate
    )


def _export_lead_vocals(
    wav_path: Path,
    mp3_path: Path,
    bitrate: str,
    on_vocals_ready: Optional[Callable[[Path], None]],
    stop_event: Optional[threading.Event],
) -> None:
    """Write vocals.mp3, then hand it to on_vocals_ready (runs on the encoder thread)."""
    _export_mp3(wav_path, mp3_path, bitrate)
    logger.info("[PIPELINE] vocals.mp3 ready at %s", mp3_path)
    if on_vocals_ready is None or (stop_event and stop_event.is_set()):
        return
    logger.info("[PIPELINE] firing on_vocals_ready callback")
    try:
        on_vocals_ready(mp3_path)
        logger.info("[PIPELINE] on_vocals_ready callback completed")
    except Exception as e:
        logger.warning("[PIPELINE] on_vocals_ready callback raised: %s", e)


def _demucs_autocast(device, enabled: bool):
    """fp16 autocast for Demucs on CUDA: ~15% faster, inaudible (listened 2026-10-10)."""
    if enabled and torch.device(device).type == "cuda":
        return torch.autocast("cuda", dtype=torch.float16)
    return contextlib.nullcontext()


def _use_vocals_specialist(separator: DemucsSeparator) -> bool:
    """
    Swap a fine-tuned bag (htdemucs_ft) for its vocals model alone.

    The bag runs four models over the whole song, each producing all four
    stems, and keeps one stem from each (one-hot weights). Only the vocals
    model's output is needed here, so running it alone is ~4x faster with the
    same vocals. Returns False and leaves a single model (e.g. htdemucs) as is.
    """
    bag = separator._model
    weights = getattr(bag, "weights", None)
    if not weights or "vocals" not in bag.sources:
        return False
    vocals_idx = bag.sources.index("vocals")
    one_hot = [1.0 if i == vocals_idx else 0.0 for i in range(len(bag.sources))]
    specialist = next(
        (m for m, w in zip(bag.models, weights) if list(w) == one_hot), None
    )
    if specialist is None:
        return False
    separator._model = specialist
    logger.info("Demucs: running only the vocals model of %s", type(bag).__name__)
    return True


def _denoise_backing(
    backing_vocals_path: Path,
    temp_dir: Path,
    status_callback: Callable[[str], None],
    stop_event: Optional[threading.Event],
) -> Path:
    """Run the de-noise model on the backing vocals; fall back to the raw backing on failure."""
    try:
        status_callback(f"Progress: 76% - Loading model: {DENOISE_MODEL}")
        denoise_separator = load_separator(DENOISE_MODEL, str(temp_dir))

        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        status_callback("Progress: 83% - Running de-noise on backing vocals...")
        denoise_output_files = denoise_separator.separate(str(backing_vocals_path))
        logger.info("De-noise produced: %s", denoise_output_files)
        del denoise_separator
        release_gpu_memory()

        # De-noise model outputs "dry" stem as the cleaned audio
        for file_path in denoise_output_files:
            file_obj = Path(file_path)
            if not file_obj.is_absolute():
                file_obj = temp_dir / file_obj.name
            if "dry" in file_obj.name.lower() and file_obj.exists():
                logger.info("Cleaned backing vocals: %s", file_obj)
                return file_obj

        logger.warning("De-noise dry stem not found, using original backing vocals")
        return backing_vocals_path

    except Exception as e:
        # Graceful fallback: use uncleaned backing if de-noise fails
        logger.warning("De-noise failed, using original backing: %s", e)
        status_callback("De-noise model unavailable, using original backing...")
        release_gpu_memory()
        return backing_vocals_path
