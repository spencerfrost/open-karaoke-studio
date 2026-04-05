"""
Celery task definitions for audio processing
"""

import json
import shutil
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Tuple

import librosa

from app.config.logging import get_structured_logger
from app.db.models import JobStatus
from app.repositories import JobRepository
from app.services import FileService, audio, file_management
from app.services.audio import create_audio_progress_mapper, detect_loudness, detect_vocal_range
from app.services.chord_detection_service import detect_chords
from app.services.separation_engines import (
    separate_with_clean_backing,
    separate_with_demucs,
    separate_with_hybrid,
    separate_with_roformer,
    separate_with_three_track,
)
from celery.utils.log import get_task_logger

from .celery_app import celery

logger = get_task_logger(__name__)
# Add structured logging for better job tracking
structured_logger = get_structured_logger(
    "app.jobs", {"job_module": "jobs", "component": "task_processor"}
)
job_repository = JobRepository()


def select_and_run_separation_engine(
    engine_type: str,
    input_path: Path,
    song_dir: Path,
    status_callback: Callable[[str], None],
    stop_event: threading.Event,
    on_vocals_ready: Optional[Callable[[Path], None]] = None,
    timing_sink: Optional[dict] = None,
) -> Tuple[bool, Optional[float]]:
    """
    Select and run the appropriate audio separation engine.

    Args:
        engine_type: Engine to use ('roformer', 'hybrid', 'clean_backing', or 'demucs')
        input_path: Path to input audio file
        song_dir: Directory to write separated tracks
        status_callback: Callback for progress updates
        stop_event: Threading event to signal cancellation
        on_vocals_ready: Optional callback invoked with the vocals.mp3 path as soon
            as lead vocals are available (three_track engine only). Use to dispatch
            vocal analysis tasks before full separation completes.
        timing_sink: Optional dict populated in-place with per-stage timestamps
            (three_track engine only). Keys: demucs_start/end, roformer_start/end,
            vocals_mp3_start/end, denoise_start/end, mp3_conversion_start/end,
            bpm_wait_start/end.

    Returns:
        Tuple of (success: bool, detected_bpm: Optional[float])
    """
    logger.info("Using separation engine: %s", engine_type)

    # Map engine types to their separation functions
    engine_map = {
        "roformer": separate_with_roformer,
        "hybrid": separate_with_hybrid,
        "clean_backing": separate_with_clean_backing,
        "three_track": separate_with_three_track,
    }

    # Get separator function, defaulting to demucs
    separator_fn = engine_map.get(engine_type, separate_with_demucs)

    kwargs: dict = dict(
        input_path=input_path,
        song_dir=song_dir,
        status_callback=status_callback,
        stop_event=stop_event,
    )
    # on_vocals_ready and timing_sink are only supported by the three_track engine
    if engine_type == "three_track" and on_vocals_ready is not None:
        kwargs["on_vocals_ready"] = on_vocals_ready
    if engine_type == "three_track" and timing_sink is not None:
        kwargs["timing_sink"] = timing_sink

    return separator_fn(**kwargs)


def _broadcast_job_event(job, was_created=False):
    """
    Broadcast a job event via WebSocket if available.

    Args:
        job: The job object
        was_created: Whether this is a newly created job
    """
    # WebSocket broadcasting has been migrated to FastAPI
    # Job events are now handled by the FastAPI WebSocket server
    # Frontend polls the database via REST API for job status updates
    pass


class AudioProcessingError(Exception):
    """Custom exception for audio processing errors"""


def get_filepath_from_job(job):
    """Get the full filepath for a job based on its filename"""
    from pathlib import Path

    from app.config import get_config

    # Construct the path to the original file based on the job's filename
    config = get_config()
    song_dir = Path(config.BASE_LIBRARY_DIR) / job.song_id
    filepath = song_dir / "original.mp3"  # Or however you determine the filename

    return str(filepath)


@celery.task(bind=True, name="process_audio_job", max_retries=3)
def process_audio_job(self, job_id, engine_type="three_track"):
    """
    Celery task to process audio file

    Args:
        job_id: Unique identifier for the job
        engine_type: Separation engine to use ('demucs', 'roformer', 'hybrid')
    """
    logger.info("Starting audio processing job for job %s", job_id)

    # Get the job from storage with retry logic
    job_repository = JobRepository()
    job = job_repository.get_by_id(job_id)
    if not job:
        if self.request.retries < self.max_retries:
            logger.warning(
                "Job %s not found, retrying in %s seconds (attempt %s/%s)",
                job_id,
                2**self.request.retries,
                self.request.retries + 1,
                self.max_retries + 1,
            )
            # Exponential backoff: 2, 4, 8 seconds
            raise self.retry(countdown=2**self.request.retries)

        logger.error("Job %s not found after %s attempts", job_id, self.max_retries + 1)
        return {"status": "error", "message": "Job not found after retries"}

    # Determine the filepath from the job
    from pathlib import Path

    from app.config import get_config

    config = get_config()
    song_id = job.song_id
    if not song_id:
        logger.error("Job %s has no associated song_id", job_id)
        return {"status": "error", "message": "No song ID associated with job"}
    song_dir = Path(config.BASE_LIBRARY_DIR) / song_id
    filepath = song_dir / "original.mp3"
    filename = filepath.name

    # Update job status to processing
    job.status = JobStatus.PROCESSING
    job.started_at = datetime.now()
    job.engine_type = engine_type
    job_repository.update(job)

    # Create a stop event (for compatibility with audio.separate_audio)
    import threading

    stop_event = threading.Event()

    def update_progress(progress, message):
        """Update job progress and log the message.

        Uses throttling to prevent database spam during frequent updates.
        Only saves to database when progress changes significantly.
        """
        # Track the last saved progress to avoid unnecessary database writes
        last_saved_progress = getattr(update_progress, "_last_saved_progress", 0)

        job.progress = progress

        # Determine if we should save to database
        # Save if progress changed by 5% or more, or is a milestone
        progress_diff = abs(progress - last_saved_progress)
        is_milestone = progress in [0, 5, 25, 50, 75, 90, 100]
        should_save = progress_diff >= 5 or is_milestone

        # Update database only on milestones — skip entirely otherwise
        if should_save:
            job_repository.update(job)
            update_progress._last_saved_progress = progress

        if hasattr(self, "update_state"):
            self.update_state(
                state="PROGRESS",
                meta={
                    "job_id": job_id,
                    "filename": filename,
                    "progress": progress,
                    "status": "processing",
                    "message": message,
                },
            )
        # Enhanced logging with structured data - only for milestones
        if should_save:
            structured_logger.info(
                "Job progress: %s%% - %s",
                progress,
                message,
                extra={
                    "job_id": job_id,
                    "progress": progress,
                    "status": "processing",
                    "filename": filename,
                    "message": message,
                },
            )
        # Only log major progress milestones to reduce noise
        if progress % 25 == 0 or progress >= 95:
            logger.info("Job %s progress: %s%% - %s", job_id, progress, message)

    try:
        file_service = FileService()
        file_service.ensure_library_exists()
        config = get_config()
        song_id = job.song_id
        if not song_id:
            raise AudioProcessingError(f"Job {job_id} has no associated song_id")
        song_dir = Path(config.BASE_LIBRARY_DIR) / song_id
        update_progress(5, f"Created directory for {job_id}")

        # Separate audio using the selected engine
        success, _ = select_and_run_separation_engine(
            engine_type=engine_type,
            input_path=filepath,
            song_dir=song_dir,
            status_callback=lambda msg: update_progress(20, msg),
            stop_event=stop_event,
        )
        if not success:
            raise AudioProcessingError("Audio separation failed")

        # Update engine_type and duration — everything else goes to post_process_song
        from app.db.database import get_db_session
        from app.repositories.song_repository import SongRepository

        with get_db_session() as session:
            repo = SongRepository(session)
            update_kwargs = {"engine_type": engine_type}
            try:
                update_kwargs["duration"] = librosa.get_duration(path=str(filepath))
            except Exception as e:
                logger.warning("Duration detection failed for job %s: %s", job_id, e)
            repo.update(song_id, **update_kwargs)

        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.completed_at = datetime.now()
        job_repository.update(job)

        _broadcast_job_event(job)

        # Dispatch secondary enrichment task (fire-and-forget)
        celery.send_task("post_process_song", args=[song_id])
        logger.info("Dispatched post_process_song for song %s", song_id)

        return {
            "status": "success",
            "job_id": job_id,
            "filename": filename,
        }

    except audio.StopProcessingError:
        job.status = JobStatus.CANCELLED
        job.error = "Processing was manually stopped"
        job.completed_at = datetime.now()
        job_repository.update(job)
        # Use song_dir here which is based on song_id, not job_id
        if song_dir.exists():
            shutil.rmtree(song_dir)
        logger.info("Job %s was cancelled", job_id)
        return {"status": "cancelled", "job_id": job_id, "filename": filename}

    except Exception as e:
        error_message = str(e)
        logger.error("Error processing job %s: %s", job_id, error_message)
        traceback.print_exc()
        job.status = JobStatus.FAILED
        job.error = error_message
        job.completed_at = datetime.now()
        job_repository.update(job)
        return {
            "status": "error",
            "job_id": job_id,
            "filename": filename,
            "error": error_message,
        }


@celery.task(bind=True, name="cleanup_old_jobs")
def cleanup_old_jobs(self):
    """
    Periodically clean up old job records and temporary files
    """
    logger.info("Running job cleanup task")
    # Implement cleanup logic here


def _fetch_thumbnail_safe(
    youtube_service, video_id: str, song_id: str
) -> Optional[str]:
    """Fetch thumbnail in a background thread. Returns URL on success, None on failure."""
    try:
        url = youtube_service.fetch_and_save_thumbnail(video_id, song_id)
        logger.info("Background thumbnail download complete for video %s", video_id)
        return url
    except Exception as e:
        logger.warning("Background thumbnail download failed for %s: %s", video_id, e)
        return None


def _run_post_processing(song_id: str, song_dir: Path) -> None:
    """Run all enrichment steps after audio separation. Each step is independent — failures are logged only."""
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    vocals_path = song_dir / "vocals.mp3"
    instrumental_path = song_dir / "instrumental.mp3"
    update_kwargs = {}

    try:
        if vocals_path.exists():
            vocal_range = detect_vocal_range(
                vocals_path, lambda msg: logger.debug("VocalRange: %s", msg)
            )
            if vocal_range:
                update_kwargs["vocal_range_low"] = vocal_range[0]
                update_kwargs["vocal_range_high"] = vocal_range[1]
    except Exception as e:
        logger.warning("Vocal range detection failed for song %s: %s", song_id, e)

    try:
        if instrumental_path.exists():
            chord_data = detect_chords(str(instrumental_path))
            if chord_data:
                update_kwargs["chords_data"] = chord_data
    except Exception as e:
        logger.warning("Chord detection failed for song %s: %s", song_id, e)

    try:
        if instrumental_path.exists():
            loudness_result = detect_loudness(
                instrumental_path, lambda msg: logger.debug("Loudness: %s", msg)
            )
            if loudness_result:
                update_kwargs["loudness_dbfs"] = loudness_result[0]
                update_kwargs["gain_db"] = loudness_result[1]
    except Exception as e:
        logger.warning("Loudness detection failed for song %s: %s", song_id, e)

    # Fetch album art (iTunes first, YouTube thumbnail as fallback)
    try:
        with get_db_session() as session:
            repo = SongRepository(session)
            song = repo.fetch(song_id)
            song_title = song.title if song else None
            song_artist = song.artist if song else None
            video_id = song.video_id if song else None

        album_art_assigned = False
        if song_title and song_artist:
            from app.services.itunes_service import fetch_and_assign_album_art

            album_art_assigned = fetch_and_assign_album_art(song_id, song_title, song_artist)
            if album_art_assigned:
                logger.info("Album art downloaded for song %s", song_id)

        if not album_art_assigned and video_id:
            from app.services.youtube_service import YouTubeService

            youtube_service = YouTubeService()
            youtube_service.fetch_and_save_thumbnail(video_id, song_id)
            logger.info("Thumbnail downloaded for song %s (iTunes had no match)", song_id)
    except Exception as e:
        logger.warning("Artwork fetch failed for song %s: %s", song_id, e)

    if update_kwargs:
        with get_db_session() as session:
            repo = SongRepository(session)
            repo.update(song_id, **update_kwargs)
        logger.info("Post-processing complete for song %s (%s fields updated)", song_id, len(update_kwargs))

    # AcoustID fingerprinting — identify the track by audio content
    # Prefer original.mp3 (full mix) — stems are acoustically degraded and produce unreliable matches
    try:
        original_path = song_dir / "original.mp3"
        audio_path = (
            original_path if original_path.exists()
            else instrumental_path if instrumental_path.exists()
            else vocals_path
        )
        if audio_path.exists():
            from app.services.acoustid_service import AcoustIdService

            with get_db_session() as session:
                repo = SongRepository(session)
                AcoustIdService(repo).fingerprint_and_identify(song_id, audio_path)
        else:
            logger.warning("AcoustID: no audio file found for song %s", song_id)
    except Exception:
        logger.warning("AcoustID fingerprinting failed for song %s", song_id, exc_info=True)

    # Populate song_artists join table (regex-based; AcoustID may overwrite if it auto-corrects)
    try:
        from app.services.song_artist_service import populate_song_artists

        with get_db_session() as session:
            repo = SongRepository(session)
            song = repo.fetch(song_id)
            if song and song.artist:
                populate_song_artists(session, song, song.artist)
    except Exception:
        logger.warning("song_artists population failed for song %s", song_id, exc_info=True)

    # Word-level alignment — runs after processing if lyrics are available
    try:
        if vocals_path.exists():
            import json as _json

            from app.db.database import get_db_session as _get_db
            from app.repositories.song_repository import SongRepository as _SongRepo
            from app.services.lyrics_alignment import (
                align_lyrics_to_vocals,
                align_plain_lyrics_to_vocals,
            )

            MIN_SCORE = 0.5

            with _get_db() as session:
                song = _SongRepo(session).fetch(song_id)
                if not song:
                    logger.debug("Song %s not found for alignment", song_id)
                else:
                    source_content = song.synced_lyrics
                    use_plain = source_content is None
                    if use_plain:
                        source_content = song.plain_lyrics

                    if source_content:
                        logger.info(
                            "Running word-level alignment for song %s (source=%s)",
                            song_id,
                            "plain" if use_plain else "synced",
                        )
                        if use_plain:
                            result = align_plain_lyrics_to_vocals(source_content, vocals_path)
                        else:
                            result = align_lyrics_to_vocals(source_content, vocals_path)

                        if result and result["mean_score"] >= MIN_SCORE:
                            song.word_synced_lyrics = _json.dumps({
                                "words": result["words"],
                                "language": result["language"],
                                "mean_score": result["mean_score"],
                                "word_count": result["word_count"],
                                "line_count": result["line_count"],
                                "aligned_at": result["aligned_at"],
                            })
                            session.commit()
                            logger.info(
                                "Alignment stored: %d words, mean_score=%.3f for song %s",
                                result["word_count"],
                                result["mean_score"],
                                song_id,
                            )
                        elif result:
                            logger.info(
                                "Alignment skipped (low confidence mean_score=%.3f) for song %s",
                                result["mean_score"],
                                song_id,
                            )
                        else:
                            logger.warning("Alignment produced no result for song %s", song_id)
                    else:
                        logger.debug("No lyrics to align for song %s", song_id)
    except Exception:
        logger.warning("Word-level alignment failed for song %s", song_id, exc_info=True)


@celery.task(bind=True, name="post_process_song")
def post_process_song(self, song_id: str) -> None:
    """
    DEPRECATED: Serial enrichment task — replaced by per-step tasks dispatched
    from process_youtube_job as soon as each required input is available:
      fetch_song_artwork     — dispatched at job start (~5%)
      fingerprint_single_song — dispatched after download (~30%)
      detect_song_loudness   — dispatched after download (~30%)
      detect_song_vocal_range — dispatched when vocals.mp3 ready (~62%)
      align_song_lyrics       — dispatched when vocals.mp3 ready (~62%)
      detect_song_chords      — dispatched after full separation (~90%)

    Still called by process_audio_job (upload flow) — do not delete until that
    path is refactored to use per-step dispatch as well.
    """
    logger.info("Starting post-processing for song %s", song_id)

    from pathlib import Path

    from app.config import get_config

    config = get_config()
    song_dir = Path(config.BASE_LIBRARY_DIR) / song_id

    if not song_dir.exists():
        logger.error("post_process_song: song directory not found for song %s", song_id)
        return

    try:
        _run_post_processing(song_id, song_dir)
    except Exception as e:
        logger.error("post_process_song failed for song %s: %s", song_id, e, exc_info=True)


# ---------------------------------------------------------------------------
# Per-step enrichment tasks — dispatched as soon as their required input exists
# ---------------------------------------------------------------------------


@celery.task(name="fetch_song_artwork")
def fetch_song_artwork(song_id: str) -> dict:
    """Fetch album art via iTunes (falling back to YouTube thumbnail). No audio required."""
    logger.info("[PIPELINE] fetch_song_artwork starting for song %s", song_id)
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.itunes_service import fetch_and_assign_album_art

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if not song:
            logger.warning("fetch_song_artwork: song %s not found", song_id)
            return {"status": "not_found", "song_id": song_id}
        song_title = song.title
        song_artist = song.artist
        video_id = song.video_id

    assigned = False
    if song_title and song_artist:
        try:
            assigned = fetch_and_assign_album_art(song_id, song_title, song_artist)
            if assigned:
                logger.info("fetch_song_artwork: iTunes art assigned for song %s", song_id)
        except Exception:
            logger.warning("fetch_song_artwork: iTunes lookup failed for song %s", song_id, exc_info=True)

    if not assigned and video_id:
        try:
            from app.services.youtube_service import YouTubeService

            YouTubeService().fetch_and_save_thumbnail(video_id, song_id)
            logger.info("fetch_song_artwork: YouTube thumbnail saved for song %s", song_id)
        except Exception:
            logger.warning("fetch_song_artwork: thumbnail download failed for song %s", song_id, exc_info=True)

    return {"status": "ok", "song_id": song_id}


@celery.task(name="detect_song_loudness")
def detect_song_loudness(song_id: str) -> dict:
    """Measure loudness from original.mp3 and store gain correction value."""
    logger.info("[PIPELINE] detect_song_loudness starting for song %s", song_id)
    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    config = get_config()
    audio_path = Path(config.BASE_LIBRARY_DIR) / song_id / "original.mp3"

    if not audio_path.exists():
        logger.warning("detect_song_loudness: original.mp3 not found for song %s", song_id)
        return {"status": "no_audio", "song_id": song_id}

    try:
        result = detect_loudness(audio_path, lambda msg: logger.debug("Loudness: %s", msg))
    except Exception:
        logger.warning("detect_song_loudness: failed for song %s", song_id, exc_info=True)
        return {"status": "error", "song_id": song_id}

    if result:
        with get_db_session() as session:
            from app.repositories.song_repository import SongRepository as _Repo
            _Repo(session).update(song_id, loudness_dbfs=result[0], gain_db=result[1])
        logger.info("detect_song_loudness: %.2f dBFS (gain %.2f dB) for song %s", result[0], result[1], song_id)

    return {"status": "ok", "song_id": song_id}


@celery.task(name="detect_song_vocal_range")
def detect_song_vocal_range(song_id: str) -> dict:
    """Detect vocal pitch range from vocals.mp3 and store note names."""
    logger.info("[PIPELINE] detect_song_vocal_range starting for song %s", song_id)
    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    config = get_config()
    vocals_path = Path(config.BASE_LIBRARY_DIR) / song_id / "vocals.mp3"

    if not vocals_path.exists():
        logger.warning("detect_song_vocal_range: vocals.mp3 not found for song %s", song_id)
        return {"status": "no_audio", "song_id": song_id}

    try:
        result = detect_vocal_range(vocals_path, lambda msg: logger.debug("VocalRange: %s", msg))
    except Exception:
        logger.warning("detect_song_vocal_range: failed for song %s", song_id, exc_info=True)
        return {"status": "error", "song_id": song_id}

    if result:
        with get_db_session() as session:
            SongRepository(session).update(song_id, vocal_range_low=result[0], vocal_range_high=result[1])
        logger.info("detect_song_vocal_range: %s–%s for song %s", result[0], result[1], song_id)

    return {"status": "ok", "song_id": song_id}


@celery.task(name="align_song_lyrics")
def align_song_lyrics(song_id: str) -> dict:
    """Run WhisperX forced alignment against vocals.mp3 and store word-level timings."""
    logger.info("[PIPELINE] align_song_lyrics starting for song %s", song_id)
    import json as _json

    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.lyrics_alignment import align_lyrics_to_vocals, align_plain_lyrics_to_vocals

    MIN_SCORE = 0.5

    config = get_config()
    vocals_path = Path(config.BASE_LIBRARY_DIR) / song_id / "vocals.mp3"

    if not vocals_path.exists():
        logger.warning("align_song_lyrics: vocals.mp3 not found for song %s", song_id)
        return {"status": "no_audio", "song_id": song_id}

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if not song:
            logger.warning("align_song_lyrics: song %s not found", song_id)
            return {"status": "not_found", "song_id": song_id}
        source_content = song.synced_lyrics
        use_plain = source_content is None
        if use_plain:
            source_content = song.plain_lyrics

    if not source_content:
        logger.debug("align_song_lyrics: no lyrics available for song %s", song_id)
        return {"status": "no_lyrics", "song_id": song_id}

    try:
        if use_plain:
            result = align_plain_lyrics_to_vocals(source_content, vocals_path)
        else:
            result = align_lyrics_to_vocals(source_content, vocals_path)
    except Exception:
        logger.warning("align_song_lyrics: alignment failed for song %s", song_id, exc_info=True)
        return {"status": "error", "song_id": song_id}

    if not result:
        logger.warning("align_song_lyrics: no result produced for song %s", song_id)
        return {"status": "no_result", "song_id": song_id}

    if result["mean_score"] < MIN_SCORE:
        logger.info(
            "align_song_lyrics: low confidence (%.3f < %.1f), skipping for song %s",
            result["mean_score"], MIN_SCORE, song_id,
        )
        return {"status": "low_confidence", "song_id": song_id}

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if song:
            song.word_synced_lyrics = _json.dumps({
                "words": result["words"],
                "language": result["language"],
                "mean_score": result["mean_score"],
                "word_count": result["word_count"],
                "line_count": result["line_count"],
                "aligned_at": result["aligned_at"],
            })
            session.commit()
    logger.info(
        "align_song_lyrics: %d words stored (mean_score=%.3f) for song %s",
        result["word_count"], result["mean_score"], song_id,
    )
    return {"status": "ok", "song_id": song_id}


@celery.task(name="detect_song_chords")
def detect_song_chords(song_id: str) -> dict:
    """Detect chord progression from instrumental.mp3 and store beat-synced chord list."""
    logger.info("[PIPELINE] detect_song_chords starting for song %s", song_id)
    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    config = get_config()
    instrumental_path = Path(config.BASE_LIBRARY_DIR) / song_id / "instrumental.mp3"

    if not instrumental_path.exists():
        logger.warning("detect_song_chords: instrumental.mp3 not found for song %s", song_id)
        return {"status": "no_audio", "song_id": song_id}

    try:
        chord_data = detect_chords(str(instrumental_path))
    except Exception:
        logger.warning("detect_song_chords: failed for song %s", song_id, exc_info=True)
        return {"status": "error", "song_id": song_id}

    if chord_data:
        with get_db_session() as session:
            SongRepository(session).update(song_id, chords_data=chord_data)
        logger.info("detect_song_chords: %d chords stored for song %s", len(chord_data), song_id)

    return {"status": "ok", "song_id": song_id}


@celery.task(name="batch_fingerprint_songs")
def batch_fingerprint_songs(reprocess_all: bool = False) -> None:
    """
    Batch Celery task: fingerprint songs via AcoustID.
    By default only processes songs with status='not_checked'.
    Pass reprocess_all=True to re-fingerprint every song (clears prior results).
    """
    from app.config import get_config
    from app.db.database import get_db_session
    from app.db.models.song import DbSong
    from app.repositories.song_repository import SongRepository
    from app.services.acoustid_service import AcoustIdService

    config = get_config()

    with get_db_session() as session:
        query = session.query(DbSong.id)
        if not reprocess_all:
            query = query.filter(DbSong.acoustid_fingerprint_status == "not_checked")
        song_ids = [row[0] for row in query.all()]

    logger.info("batch_fingerprint_songs: processing %d songs", len(song_ids))

    for song_id in song_ids:
        song_dir = config.BASE_LIBRARY_DIR / song_id
        original_path = song_dir / "original.mp3"
        instrumental_path = song_dir / "instrumental.mp3"
        vocals_path = song_dir / "vocals.mp3"
        audio_path = (
            original_path if original_path.exists()
            else instrumental_path if instrumental_path.exists()
            else vocals_path
        )

        if not audio_path.exists():
            logger.warning("batch_fingerprint_songs: no audio for song %s, skipping", song_id)
            with get_db_session() as session:
                SongRepository(session).update(song_id, acoustid_fingerprint_status="failed")
            continue

        try:
            with get_db_session() as session:
                AcoustIdService(SongRepository(session)).fingerprint_and_identify(song_id, audio_path)
        except Exception:
            logger.warning("batch_fingerprint_songs: error processing song %s", song_id, exc_info=True)

    logger.info("batch_fingerprint_songs: done")


@celery.task(name="batch_backfill_artwork")
def batch_backfill_artwork(force: bool = False) -> dict:
    """
    Batch Celery task: backfill album art for songs missing it.
    By default only processes songs with album_id IS NULL.
    Pass force=True to reprocess every song.
    """
    from app.db.database import get_db_session
    from app.db.models.song import DbSong
    from app.services.itunes_service import fetch_and_assign_album_art

    with get_db_session() as session:
        query = session.query(DbSong.id, DbSong.title, DbSong.artist)
        if not force:
            query = query.filter(DbSong.album_id.is_(None))
        rows = query.all()

    song_ids = [(row[0], row[1], row[2]) for row in rows]
    logger.info("batch_backfill_artwork: processing %d songs", len(song_ids))

    success = 0
    skipped = 0
    for i, (song_id, title, artist) in enumerate(song_ids):
        if not title or not artist:
            skipped += 1
            continue
        # Baseline delay to stay well under the iTunes rate limit
        if i > 0:
            import time
            time.sleep(1.5)
        try:
            got = fetch_and_assign_album_art(song_id, title, artist)
            if got:
                success += 1
            else:
                skipped += 1
        except Exception:
            logger.warning("batch_backfill_artwork: error for song %s", song_id, exc_info=True)
            skipped += 1

    logger.info("batch_backfill_artwork: done — %d succeeded, %d skipped", success, skipped)
    return {"processed": len(song_ids), "success": success, "skipped": skipped}


@celery.task(name="batch_backfill_duration")
def batch_backfill_duration(mode: str = "missing") -> dict:
    """
    Batch Celery task: populate duration from the original audio file.

    mode="missing" — only processes songs where duration IS NULL.
    mode="all"     — processes every song in the library.
    """
    from pathlib import Path

    import librosa

    from app.config import get_config
    from app.db.database import get_db_session
    from app.db.models.song import DbSong
    from app.repositories.song_repository import SongRepository

    config = get_config()

    with get_db_session() as session:
        query = session.query(DbSong.id)
        if mode == "missing":
            query = query.filter(DbSong.duration.is_(None))
        rows = query.all()

    song_ids = [row[0] for row in rows]
    logger.info("batch_backfill_duration: processing %d songs (mode=%s)", len(song_ids), mode)

    success = 0
    skipped = 0
    for song_id in song_ids:
        audio_path = Path(config.BASE_LIBRARY_DIR) / song_id / "original.mp3"
        if not audio_path.exists():
            skipped += 1
            continue
        try:
            duration = librosa.get_duration(path=str(audio_path))
            with get_db_session() as session:
                SongRepository(session).update(song_id, duration=duration)
            success += 1
        except Exception:
            logger.warning("batch_backfill_duration: error for song %s", song_id, exc_info=True)
            skipped += 1

    logger.info("batch_backfill_duration: done — %d updated, %d skipped", success, skipped)
    return {"processed": len(song_ids), "success": success, "skipped": skipped}


@celery.task(name="fingerprint_single_song")
def fingerprint_single_song(song_id: str) -> dict:
    """Fingerprint a single song via AcoustID."""
    from pathlib import Path

    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.acoustid_service import AcoustIdService

    config = get_config()
    song_dir = Path(config.BASE_LIBRARY_DIR) / song_id
    original = song_dir / "original.mp3"
    instrumental = song_dir / "instrumental.mp3"
    vocals = song_dir / "vocals.mp3"
    audio_path = (
        original if original.exists()
        else instrumental if instrumental.exists()
        else vocals if vocals.exists()
        else None
    )

    with get_db_session() as session:
        if audio_path is None:
            logger.warning("fingerprint_single_song: no audio file found for song %s", song_id)
            SongRepository(session).update(song_id, acoustid_fingerprint_status="failed")
            return {"status": "no_audio", "song_id": song_id}
        try:
            AcoustIdService(SongRepository(session)).fingerprint_and_identify(song_id, audio_path)
        except Exception:
            logger.exception("fingerprint_single_song: failed for song %s", song_id)

    # AcoustID may have corrected title/artist — resolve credits against latest data
    logger.info("[PIPELINE] fingerprint complete — dispatching enrich_song_artist_credits for song %s", song_id)
    celery.send_task("enrich_song_artist_credits", args=[song_id])

    return {"status": "ok", "song_id": song_id}


@celery.task(name="enrich_song_artist_credits")
def enrich_song_artist_credits(song_id: str) -> dict:
    """Re-resolve artist credits for a single song using MB recording → MB search → regex."""
    from app.db.database import get_db_session
    from app.db.models.song_artist import DbSongArtist
    from app.repositories.artist_repository import ArtistRepository
    from app.repositories.song_repository import SongRepository
    from app.services.credits_resolver import resolve_artist_credits
    from app.services.song_artist_service import try_ampersand_split

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if not song:
            logger.warning("enrich_song_artist_credits: song %s not found", song_id)
            return {"status": "not_found", "song_id": song_id}

        credits = resolve_artist_credits(
            title=song.title,
            artist_str=song.artist,
            recording_id=song.musicbrainz_recording_id,
        )

        # If MB/regex left a single primary with "&", try heuristic DB-based split
        credits = try_ampersand_split(credits, session)

        artist_repo = ArtistRepository(session)

        # Clear existing links
        session.query(DbSongArtist).filter(DbSongArtist.song_id == song.id).delete()

        first_primary_set = False
        for i, (name, role) in enumerate(credits):
            artist = artist_repo.get_or_create(name, display_name=name)
            if not first_primary_set and role == "primary":
                song.artist_id = artist.id
                first_primary_set = True
            session.add(
                DbSongArtist(
                    song_id=song.id,
                    artist_id=artist.id,
                    role=role,
                    display_order=i,
                )
            )

        session.commit()
        logger.info(
            "Enriched song_artists for song %s: %s",
            song_id,
            [(n, r) for n, r in credits],
        )

    return {"status": "ok", "song_id": song_id}


@celery.task(name="batch_align_lyrics")
def batch_align_lyrics(mode: str = "missing", language: str = "en") -> dict:
    """
    Batch Celery task: run WhisperX forced alignment across the library.

    mode="missing" — only processes songs without an active word_synced row.
    mode="all"     — re-runs alignment on every song with vocals + lyrics.

    Loads the wav2vec2 model once and reuses it across all songs.
    """
    import json as _json

    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.file_service import FileService
    from app.services.lyrics_alignment import (
        align_lyrics_to_vocals_with_model,
        align_plain_lyrics_to_vocals_with_model,
        load_alignment_model,
    )

    MIN_SCORE = 0.5
    file_service = FileService()

    with get_db_session() as session:
        all_songs = SongRepository(session).fetch_all()
        song_ids = [s.id for s in all_songs]

    logger.info("batch_align_lyrics: found %d songs (mode=%s)", len(song_ids), mode)

    eligible = []
    for song_id in song_ids:
        vocals_path = file_service.get_vocals_path(song_id, ".mp3")
        if not vocals_path.exists():
            continue
        with get_db_session() as session:
            song = SongRepository(session).fetch(song_id)
            if not song:
                continue
            if mode == "missing" and song.word_synced_lyrics:
                continue
            if not song.synced_lyrics and not song.plain_lyrics:
                continue
        eligible.append(song_id)

    total_songs = len(song_ids)
    if not eligible:
        logger.info("batch_align_lyrics: no eligible songs — done")
        return {
            "processed": 0, "activated": 0, "failed": 0,
            "skipped": total_songs, "results": [],
        }

    logger.info("batch_align_lyrics: loading wav2vec2 model for %d songs", len(eligible))
    model_a, metadata = load_alignment_model(language=language)

    results = []
    activated = 0
    failed = 0

    for song_id in eligible:
        vocals_path = file_service.get_vocals_path(song_id, ".mp3")
        with get_db_session() as session:
            song = SongRepository(session).fetch(song_id)
            if not song:
                failed += 1
                results.append({"songId": song_id, "status": "failed", "reason": "song not found"})
                continue
            source_content = song.synced_lyrics
            use_plain = source_content is None
            if use_plain:
                source_content = song.plain_lyrics
            song_label = f"{song.artist or '?'} — {song.title or song_id}"

        if not source_content:
            failed += 1
            results.append({"songId": song_id, "title": song_label, "status": "failed", "reason": "no source lyrics"})
            continue

        try:
            result = (
                align_plain_lyrics_to_vocals_with_model(
                    source_content, vocals_path, model_a, metadata, language=language
                )
                if use_plain
                else align_lyrics_to_vocals_with_model(
                    source_content, vocals_path, model_a, metadata, language=language
                )
            )

            if not result:
                failed += 1
                results.append({"songId": song_id, "title": song_label, "status": "failed", "reason": "no words returned"})
                continue

            confident = result["mean_score"] >= MIN_SCORE
            if confident:
                with get_db_session() as session:
                    song = SongRepository(session).fetch(song_id)
                    song.word_synced_lyrics = _json.dumps({
                        "words": result["words"],
                        "language": result["language"],
                        "mean_score": result["mean_score"],
                        "word_count": result["word_count"],
                        "line_count": result["line_count"],
                        "aligned_at": result["aligned_at"],
                    })
                    session.commit()
                activated += 1
                status = "activated"
            else:
                status = "low_confidence"

            results.append({
                "songId": song_id,
                "title": song_label,
                "status": status,
                "meanScore": result["mean_score"],
                "wordCount": result["word_count"],
                "sourceType": "plain" if use_plain else "synced",
            })
            logger.info("batch_align_lyrics %s: %s (score=%.3f)", song_label, status, result["mean_score"])

        except Exception as e:
            failed += 1
            logger.error("batch_align_lyrics failed for %s: %s", song_label, e, exc_info=True)
            results.append({"songId": song_id, "title": song_label, "status": "failed", "reason": str(e)})

    logger.info(
        "batch_align_lyrics: done — activated=%d, failed=%d",
        activated, failed,
    )
    return {
        "processed": len(eligible),
        "activated": activated,
        "failed": failed,
        "skipped": total_songs - len(eligible),
        "results": results,
    }


def _write_pipeline_timing(
    job_id: str,
    song_id: str,
    engine_type: str,
    metadata: dict,
    timestamps: dict,
    status: str,
    error: Optional[str] = None,
) -> None:
    """
    Append one JSON line to logs/pipeline_timing.jsonl recording wall-clock
    durations for each pipeline stage.  All durations are in seconds.

    Top-level keys:
      recorded_at      — ISO-8601 UTC timestamp of when the record was written
      job_id / song_id / engine_type / status
      title / artist   — from job metadata
      durations        — dict of stage_name → seconds (derived from timestamps)
      engine_stages    — per-stage timings inside the separation engine (three_track only)
      raw_timestamps   — the raw perf_counter values (relative, useful for sequencing)
    """
    from app.config import get_config

    config = get_config()
    log_path = Path(config.LOG_DIR) / "pipeline_timing.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def _dur(start_key: str, end_key: str, ts: dict) -> Optional[float]:
        s, e = ts.get(start_key), ts.get(end_key)
        if s is not None and e is not None:
            return round(e - s, 3)
        return None

    ts = timestamps
    engine_ts = ts.get("engine", {})

    durations: dict = {}
    d = _dur("download_start", "download_end", ts)
    if d is not None:
        durations["download"] = d
    d = _dur("separation_start", "separation_end", ts)
    if d is not None:
        durations["separation_total"] = d
    d = _dur("job_start", "job_end", ts)
    if d is not None:
        durations["job_total"] = d

    engine_durations: dict = {}
    for stage, start_key, end_key in [
        ("demucs", "demucs_start", "demucs_end"),
        ("roformer", "roformer_start", "roformer_end"),
        ("vocals_mp3", "vocals_mp3_start", "vocals_mp3_end"),
        ("denoise", "denoise_start", "denoise_end"),
        ("mp3_conversion", "mp3_conversion_start", "mp3_conversion_end"),
        ("bpm_wait", "bpm_wait_start", "bpm_wait_end"),
    ]:
        d = _dur(start_key, end_key, engine_ts)
        if d is not None:
            engine_durations[stage] = d

    record = {
        "recorded_at": datetime.utcnow().isoformat() + "Z",
        "job_id": job_id,
        "song_id": song_id,
        "engine_type": engine_type,
        "status": status,
        "title": metadata.get("title"),
        "artist": metadata.get("artist"),
        "durations": durations,
        "engine_stages": engine_durations,
        "raw_timestamps": {k: round(v, 6) for k, v in ts.items() if isinstance(v, float)},
    }
    if error:
        record["error"] = error

    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(record) + "\n")
        logger.info(
            "Pipeline timing logged for job %s → %s (total: %ss)",
            job_id,
            log_path,
            durations.get("job_total", "?"),
        )
    except Exception:
        logger.warning("Failed to write pipeline timing log for job %s", job_id, exc_info=True)


@celery.task(bind=True, name="process_youtube_job", max_retries=3)
def process_youtube_job(self, job_id, video_id, metadata, engine_type="three_track"):
    """
    Unified task for processing YouTube videos from start to finish

    Args:
        job_id: Job identifier
        video_id: YouTube video ID
        metadata: Dict with artist, title, album, etc.
        engine_type: Separation engine to use ('demucs', 'roformer', 'hybrid')
    """
    logger.info(
        "Starting unified YouTube processing job for job %s (artist: %s, title: %s, video_id: %s)",
        job_id,
        metadata.get("artist"),
        metadata.get("title"),
        video_id,
    )

    # Timing: record wall-clock timestamps at each pipeline milestone.
    # Written to logs/pipeline_timing.jsonl at job end for offline analysis.
    _t: dict[str, float] = {"job_start": time.perf_counter()}

    # Get the job from storage using repository
    job_repository = JobRepository()
    job = job_repository.get_by_id(job_id)
    if not job:
        logger.error("Job %s not found for video_id %s", job_id, video_id)
        return {"status": "error", "message": "Job not found"}

    # Get the song_id from the job
    song_id = job.song_id
    if not song_id:
        logger.error("Job %s has no associated song_id", job_id)
        return {"status": "error", "message": "No song ID associated with job"}

    # Verify the song exists
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    with get_db_session() as session:
        repo = SongRepository(session)
        db_song = repo.fetch(song_id)
    if not db_song:
        logger.error("Song %s not found for job %s", song_id, job_id)
        # Mark job as failed
        job.status = JobStatus.FAILED
        job.error = f"Song {song_id} not found in database"
        job.completed_at = datetime.now()
        job_repository.update(job)
        return {"status": "error", "message": f"Song {song_id} not found"}

    # Update job status to downloading
    job.status = JobStatus.DOWNLOADING
    job.status_message = "Downloading video from YouTube"
    job.started_at = datetime.now()
    job.progress = 5
    job.engine_type = engine_type
    job_repository.update(job)

    # Dispatch artwork early — no audio dependency, only needs title/artist from DB
    celery.send_task("fetch_song_artwork", args=[song_id])
    logger.info("[PIPELINE] ~5%% — dispatched fetch_song_artwork for song %s", song_id)

    def update_progress(progress, message, status=None):
        """Update job progress and status.

        Uses throttling to prevent database spam during frequent updates.
        Only saves to database when progress changes significantly or status changes.
        """
        # Track the last saved progress to avoid unnecessary database writes
        last_saved_progress = getattr(update_progress, "_last_saved_progress", 0)
        last_saved_status = getattr(update_progress, "_last_saved_status", None)

        job.progress = progress
        job.status_message = message
        if status:
            job.status = status

        # Determine if we should save to database
        # Save if: status changed, progress changed by 5% or more, or is a milestone
        progress_diff = abs(progress - last_saved_progress)
        status_changed = status and status != last_saved_status
        is_milestone = progress in [
            0, 5, 10, 12, 50, 60, 70, 73, 80, 90, 93, 95, 99, 100,
        ]
        should_save = status_changed or progress_diff >= 5 or is_milestone

        # Update database only on milestones or status changes — skip entirely otherwise
        if should_save:
            job_repository.update(job)
            update_progress._last_saved_progress = progress
            update_progress._last_saved_status = job.status

        if hasattr(self, "update_state"):
            self.update_state(
                state="PROGRESS",
                meta={
                    "job_id": job_id,
                    "progress": progress,
                    "status": job.status.value,
                    "message": message,
                },
            )
        # Only log major progress milestones to reduce noise
        if progress % 25 == 0 or progress >= 95:
            logger.info("Job %s: %s%% - %s", job_id, progress, message)

    try:
        # Phase 1: Download (5-30% progress)
        from pathlib import Path

        from app.config import get_config
        from app.services.youtube_service import YouTubeService

        config = get_config()
        youtube_service = YouTubeService()
        file_service = FileService()
        file_service.ensure_library_exists()

        song_id = job.song_id
        if not song_id:
            raise AudioProcessingError(f"Job {job_id} has no associated song_id")
        song_dir = Path(config.BASE_LIBRARY_DIR) / song_id

        update_progress(10, "Starting YouTube download")
        _t["download_start"] = time.perf_counter()

        youtube_service.download_video(
            video_id_or_url=video_id,
            song_id=song_id,
            artist=metadata.get("artist"),
            title=metadata.get("title"),
        )

        _t["download_end"] = time.perf_counter()
        update_progress(
            12,
            f"Download complete, preparing {engine_type} engine",
            JobStatus.PROCESSING,
        )

        # Dispatch tasks that only need original.mp3
        celery.send_task("fingerprint_single_song", args=[song_id])
        celery.send_task("detect_song_loudness", args=[song_id])
        logger.info("[PIPELINE] ~12%% — dispatched fingerprint_single_song + detect_song_loudness for song %s", song_id)

        # Phase 2: Audio Processing (30-90% progress)
        original_file = song_dir / "original.mp3"

        if not original_file.exists():
            raise AudioProcessingError(
                f"Original audio file not found: {original_file}"
            )

        import threading

        stop_event = threading.Event()

        _t["separation_start"] = time.perf_counter()
        update_progress(12, f"Initializing {engine_type} audio processing")

        audio_progress_callback = create_audio_progress_mapper(
            engine_type=engine_type,
            base_start=12,
            base_end=50,
            update_fn=lambda prog, msg: update_progress(
                prog, f"Audio processing: {msg}"
            ),
        )

        def on_vocals_ready(vocals_path: Path) -> None:
            """Dispatch vocal analysis tasks as soon as vocals.mp3 is available (~70%)."""
            _t["vocals_ready"] = time.perf_counter()
            logger.info(
                "[PIPELINE] ~70%% — vocals.mp3 ready (%s bytes), dispatching detect_song_vocal_range + align_song_lyrics for song %s",
                vocals_path.stat().st_size if vocals_path.exists() else "missing",
                song_id,
            )
            celery.send_task("detect_song_vocal_range", args=[song_id])
            celery.send_task("align_song_lyrics", args=[song_id])
            logger.info("[PIPELINE] ~70%% — detect_song_vocal_range + align_song_lyrics queued for song %s", song_id)

        success, _ = select_and_run_separation_engine(
            engine_type=engine_type,
            input_path=original_file,
            song_dir=song_dir,
            status_callback=audio_progress_callback,
            stop_event=stop_event,
            on_vocals_ready=on_vocals_ready,
            timing_sink=_t.setdefault("engine", {}),
        )
        _t["separation_end"] = time.perf_counter()
        if not success:
            raise AudioProcessingError("Audio separation failed")

        # Update engine_type and duration — everything else goes to post_process_song
        try:
            with get_db_session() as session:
                repo = SongRepository(session)
                update_fields = {"engine_type": engine_type}
                try:
                    update_fields["duration"] = librosa.get_duration(
                        path=str(original_file)
                    )
                except Exception as e:
                    logger.warning("Duration detection failed for song %s: %s", song_id, e)
                repo.update(song_id, **update_fields)
        except Exception as e:
            logger.error("Error updating song metadata for song %s: %s", song_id, e)

        _t["job_end"] = time.perf_counter()
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.status_message = "Processing complete"
        job.completed_at = datetime.now()
        job_repository.update(job)

        _broadcast_job_event(job)

        # Dispatch chord detection — requires instrumental.mp3 which is now available
        celery.send_task("detect_song_chords", args=[song_id])
        logger.info("[PIPELINE] ~100%% — dispatched detect_song_chords for song %s", song_id)

        _write_pipeline_timing(job_id, song_id, engine_type, metadata, _t, status="completed")

        return {
            "status": "success",
            "job_id": job_id,
            "song_id": song_id,
        }

    except audio.StopProcessingError:
        job.status = JobStatus.CANCELLED
        job.error = "Processing was manually stopped"
        job.completed_at = datetime.now()
        job_repository.update(job)
        if song_dir.exists():
            shutil.rmtree(song_dir)
        logger.info("Job %s was cancelled", job_id)
        _t.setdefault("job_end", time.perf_counter())
        _write_pipeline_timing(job_id, song_id, engine_type, metadata, _t, status="cancelled")
        return {"status": "cancelled", "job_id": job_id}

    except Exception as e:
        error_message = str(e)
        logger.error("Error processing YouTube job %s: %s", job_id, error_message)
        traceback.print_exc()
        job.status = JobStatus.FAILED
        job.error = error_message
        job.completed_at = datetime.now()
        job_repository.update(job)
        _t.setdefault("job_end", time.perf_counter())
        _write_pipeline_timing(job_id, song_id, engine_type, metadata, _t, status="failed", error=error_message)
        return {"status": "error", "job_id": job_id, "error": error_message}


# Event system integration
def _handle_job_event(event):
    """
    Handle job events from the event system.

    This replaces the direct function calls from models.
    """
    try:
        from app.db.models import Job, JobStatus
        from app.utils.events import JobEvent

        if isinstance(event, JobEvent):
            # Reconstruct job object from event data
            job_data = event.job_data
            job = Job(
                id=job_data["id"],
                filename=job_data.get("filename", ""),
                status=JobStatus(job_data["status"]),
                title=job_data.get("title"),
                artist=job_data.get("artist"),
                status_message=job_data.get(
                    "message"
                ),  # Use status_message instead of message
                progress=job_data.get("progress", 0),
                error=job_data.get("error"),
                task_id=job_data.get("task_id"),
                song_id=job_data.get("song_id"),
                notes=job_data.get("notes"),
                created_at=job_data.get("created_at"),
                started_at=job_data.get("started_at"),
                completed_at=job_data.get("completed_at"),
                dismissed=job_data.get("dismissed", False),
            )

            # Use the existing broadcast function
            _broadcast_job_event(job, event.was_created)

    except Exception as e:
        logger.error("Error handling job event: %s", e, exc_info=True)


# Subscribe to job events when module is imported
def _setup_event_subscriptions():
    """Set up event subscriptions for the jobs module."""
    try:
        from app.utils.events import subscribe_to_job_events

        subscribe_to_job_events(_handle_job_event)
        logger.info("Jobs module subscribed to job events")
    except Exception as e:
        logger.error("Failed to set up job event subscriptions: %s", e)


# Set up subscriptions when module loads
_setup_event_subscriptions()
