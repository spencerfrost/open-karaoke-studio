"""
Experiment 3: Gold Hybrid Sequential Separation Engine

Uses Demucs for initial separation, then refines vocals with audio-separator.
This approach leverages the strengths of both libraries for maximum precision.

Pipeline:
1. Demucs: Extract vocals.wav and no_vocals.wav (instrumental)
2. audio-separator (Roformer ViperX): Split vocals into lead + backing
3. Recombine: no_vocals + backing_vocals = new instrumental

Pros: Highest precision, best vocal isolation with ViperX Roformer
Cons: Longer processing time, two-pass approach
"""

import logging
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional, Tuple

import torch
import soundfile as sf
from audio_separator.separator import Separator
from demucs.api import Separator as DemucsSeparator
from app.config import get_config
from app.services.audio import (
    create_audio_progress_mapper,
    detect_bpm,
    select_device_and_log,
    make_progress_callback,
    StopProcessingError,
)
from app.services import file_management

logger = logging.getLogger(__name__)


def separate_with_hybrid(
    input_path: Path,
    song_dir: Path,
    status_callback: Callable[[str], None],
    stop_event: Optional[threading.Event] = None,
) -> Tuple[bool, Optional[float]]:
    """
    Hybrid sequential separation using Demucs + audio-separator.

    This engine produces:
    - vocals.mp3: Lead vocals only (highest quality separation)
    - instrumental.mp3: Instrumental + backing vocals

    Args:
        input_path: Path to the input audio file
        song_dir: Path to the directory where processed files will be saved
        status_callback: Function to call with status updates
        stop_event: A threading.Event to check for stop requests

    Returns:
        Tuple of (success: bool, bpm: Optional[float])
    """
    logger.info("Starting Hybrid Sequential separation for: %s", input_path.name)
    status_callback("Engine: Hybrid Sequential (Gold Standard)")

    # Create temp directory for intermediate files
    temp_dir = song_dir / ".temp_hybrid"
    temp_dir.mkdir(exist_ok=True)

    try:
        # ===== STEP 1: Demucs Separation (35-60% progress) =====
        status_callback("Progress: 35% - Step 1/3: Running Demucs for initial separation...")

        device = select_device_and_log(status_callback)
        config = get_config()
        model_name = config.DEFAULT_MODEL

        # Create a wrapped progress callback that maps Demucs [0-100%] to job [35-60%]
        demucs_progress_callback = create_audio_progress_mapper(
            engine_type='demucs',
            base_start=35,
            base_end=60,
            update_fn=lambda prog, msg: status_callback(f"Step 1/3 (Demucs): {msg} [{prog}%]")
        )

        demucs_separator = DemucsSeparator(
            model=model_name,
            device=device,
            callback=make_progress_callback(demucs_progress_callback, stop_event),
        )

        status_callback("Separating with Demucs...")
        origin_wave, separated = demucs_separator.separate_audio_file(input_path)

        # Check for stop request
        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # Extract vocals stem
        vocals_tensor = separated.get("vocals")
        if vocals_tensor is None:
            raise Exception("Vocals stem not found in Demucs output")

        # Save vocals to temp directory for audio-separator processing
        temp_vocals_path = temp_dir / "demucs_vocals.wav"
        status_callback("Saving Demucs vocals for refinement...")

        # Convert tensor to numpy and save with soundfile
        vocals_numpy = vocals_tensor.cpu().numpy().T  # Transpose to (samples, channels)
        sf.write(
            str(temp_vocals_path),
            vocals_numpy,
            demucs_separator.samplerate,
            subtype='PCM_16'
        )
        logger.info("Demucs vocals saved to: %s", temp_vocals_path)

        # Calculate and save instrumental (all non-vocal stems)
        status_callback("Calculating Demucs instrumental...")
        instrumental_stems = [s_name for s_name in separated if s_name != "vocals"]
        if not instrumental_stems:
            raise Exception("No non-vocal stems found in Demucs output")

        instrumental_tensor = torch.zeros_like(separated[instrumental_stems[0]])
        for stem_name in instrumental_stems:
            instrumental_tensor += separated[stem_name]

        # Save Demucs instrumental (this will be the base)
        temp_instrumental_path = temp_dir / "demucs_instrumental.wav"

        # Convert tensor to numpy and save with soundfile
        instrumental_numpy = instrumental_tensor.cpu().numpy().T  # Transpose to (samples, channels)
        sf.write(
            str(temp_instrumental_path),
            instrumental_numpy,
            demucs_separator.samplerate,
            subtype='PCM_16'
        )
        logger.info("Demucs instrumental saved to: %s", temp_instrumental_path)

        # Check for stop request
        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # ===== STEP 2: audio-separator Vocal Refinement (60-75% progress) =====
        status_callback("Progress: 60% - Step 2/3: Refining vocals with audio-separator...")

        # Initialize audio-separator
        separator = Separator(
            output_dir=str(temp_dir),
            output_format="wav",
        )

        # Load the Mel-Band Roformer ViperX model for lead/backing separation
        model_name = "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt"
        status_callback(f"Loading model: {model_name}")
        separator.load_model(model_filename=model_name)

        # Separate the Demucs vocals into lead and backing
        status_callback("Progress: 67% - Splitting vocals into lead and backing...")
        logger.info("Running UVR separation on Demucs vocals")

        output_files = separator.separate(str(temp_vocals_path))
        logger.info("UVR produced output files: %s", output_files)
        status_callback("Progress: 75% - Step 2/3 complete")

        # Check for stop request
        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # Find the lead vocals and backing vocals files
        # Note: audio-separator returns relative filenames, actual files are in temp_dir
        lead_vocals_file = None
        backing_vocals_file = None

        for file_path in output_files:
            file_obj = Path(file_path)
            # If the path is relative, it's in the output directory (temp_dir)
            if not file_obj.is_absolute():
                file_obj = temp_dir / file_obj.name

            # UVR_MDXNET_KARA_2 typically outputs:
            # - (Vocals) - lead vocals
            # - (Instrumental) - backing vocals (confusing naming!)
            if "(Vocals)" in file_obj.name:
                lead_vocals_file = file_obj
            elif "(Instrumental)" in file_obj.name:
                backing_vocals_file = file_obj

        if not lead_vocals_file:
            raise Exception(f"Lead vocals not found in UVR output: {output_files}")

        logger.info("Lead vocals: %s", lead_vocals_file)
        if backing_vocals_file:
            logger.info("Backing vocals: %s", backing_vocals_file)

        # Check for stop request
        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # ===== STEP 3: Recombine Instrumental + Backing (75-85% progress) =====
        status_callback("Progress: 75% - Step 3/3: Creating final instrumental...")

        # If we have backing vocals, add them to the instrumental
        final_instrumental_path = temp_dir / "final_instrumental.wav"

        if backing_vocals_file and backing_vocals_file.exists():
            logger.info("Mixing backing vocals with instrumental")
            status_callback("Mixing backing vocals with instrumental...")

            # Load both files and mix
            import librosa
            import numpy as np

            instr_audio, sr_instr = librosa.load(
                str(temp_instrumental_path), sr=None, mono=False
            )
            backing_audio, sr_backing = librosa.load(
                str(backing_vocals_file), sr=None, mono=False
            )

            # Ensure same sample rate
            if sr_instr != sr_backing:
                backing_audio = librosa.resample(
                    backing_audio, orig_sr=sr_backing, target_sr=sr_instr
                )
                sr_backing = sr_instr

            # Mix the two
            final_instrumental = instr_audio + backing_audio

            # Save the mixed instrumental
            sf.write(str(final_instrumental_path), final_instrumental.T, sr_instr)
            logger.info("Final instrumental saved to: %s", final_instrumental_path)
        else:
            # No backing vocals, just use Demucs instrumental
            logger.info("No backing vocals found, using Demucs instrumental")
            shutil.copy(temp_instrumental_path, final_instrumental_path)

        # Check for stop request
        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # ===== STEP 4: Convert to MP3 and Move to Final Location =====
        status_callback("Progress: 80% - Converting to MP3 and finalizing...")

        vocals_final = file_management.get_vocals_path_stem(song_dir).with_suffix(".mp3")
        instrumental_final = file_management.get_instrumental_path_stem(song_dir).with_suffix(".mp3")

        # Start BPM detection in background — runs while MP3 conversions execute
        _bpm_log = lambda msg: logger.debug("BPM: %s", msg)
        bpm_executor = ThreadPoolExecutor(max_workers=1)
        bpm_future = bpm_executor.submit(detect_bpm, input_path, _bpm_log)
        logger.info("BPM detection started in background thread")

        # Convert WAV to MP3 using pydub
        from pydub import AudioSegment

        # Convert lead vocals
        lead_audio = AudioSegment.from_wav(str(lead_vocals_file))
        lead_audio.export(
            str(vocals_final),
            format="mp3",
            bitrate=config.DEFAULT_MP3_BITRATE,
        )
        logger.info("Final vocals saved to: %s", vocals_final)

        # Convert instrumental
        instr_audio = AudioSegment.from_wav(str(final_instrumental_path))
        instr_audio.export(
            str(instrumental_final),
            format="mp3",
            bitrate=config.DEFAULT_MP3_BITRATE,
        )
        logger.info("Final instrumental saved to: %s", instrumental_final)
        status_callback("Progress: 85% - Step 3/3 complete")

        # Collect BPM result (started before MP3 conversion, should already be done)
        try:
            detected_bpm = bpm_future.result(timeout=30)
            logger.info("BPM detection complete: %s BPM", detected_bpm)
            if detected_bpm:
                status_callback(f"BPM detected: {detected_bpm}")
        except Exception as e:
            logger.warning("BPM detection failed or timed out: %s", e)
            detected_bpm = None
        finally:
            bpm_executor.shutdown(wait=False)

        # Clean up temp directory
        status_callback("Cleaning up temporary files...")
        shutil.rmtree(temp_dir)
        logger.info("Temporary files cleaned up")

        status_callback(f"Hybrid separation complete for {input_path.name}!")
        logger.info("Hybrid Sequential separation completed successfully")

        return True, detected_bpm

    except StopProcessingError:
        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise

    except Exception as e:
        logger.error("Hybrid separation failed: %s", e, exc_info=True)
        status_callback(f"** Error during Hybrid separation: {e} **")

        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

        return False, None
