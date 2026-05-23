"""Primary audio pipeline Celery tasks."""

import shutil
import traceback
from datetime import datetime
from pathlib import Path

import librosa

from app.db.models import JobStatus
from app.repositories import JobRepository
from app.services import FileService, audio
from app.services.audio import create_audio_progress_mapper
from app.services.lyrics_timing import log_lyrics_event
from celery.utils.log import get_task_logger

from ._events import (
    broadcast_job_event as _broadcast_job_event,
    setup_event_subscriptions as _setup_event_subscriptions,
)
from ._shared import _create_lyrics_alignment_job, _get_lyrics_job_id
from .celery_app import celery
from .exceptions import AudioProcessingError
from .separation import run_separation_with_fallback

logger = get_task_logger(__name__)

_setup_event_subscriptions()


@celery.task(bind=True, name="process_audio_job", max_retries=3)
def process_audio_job(self, job_id, engine_type="three_track"):
    """Celery task to process uploaded audio files."""
    logger.info("Starting audio processing job for job %s", job_id)

    job_repository = JobRepository()
    job = job_repository.get_by_id(job_id)
    if not job:
        if self.request.retries < self.max_retries:
            logger.warning(
                "Job %s not found, retrying in %s seconds (attempt %s/%s)",
                job_id,
                2 ** self.request.retries,
                self.request.retries + 1,
                self.max_retries + 1,
            )
            raise self.retry(countdown=2 ** self.request.retries)

        logger.error("Job %s not found after %s attempts", job_id, self.max_retries + 1)
        return {"status": "error", "message": "Job not found after retries"}

    from app.config import get_config

    config = get_config()
    song_id = job.song_id
    if not song_id:
        logger.error("Job %s has no associated song_id", job_id)
        return {"status": "error", "message": "No song ID associated with job"}
    song_dir = Path(config.BASE_LIBRARY_DIR) / song_id
    filepath = song_dir / "original.mp3"
    filename = filepath.name

    job.status = JobStatus.PROCESSING
    job.started_at = datetime.now()
    job.engine_type = engine_type
    job_repository.update(job)

    import threading

    stop_event = threading.Event()

    def update_progress(progress, message):
        last_saved_progress = getattr(update_progress, "_last_saved_progress", 0)

        job.progress = progress
        progress_diff = abs(progress - last_saved_progress)
        is_milestone = progress in [0, 5, 25, 50, 75, 90, 100]
        should_save = progress_diff >= 5 or is_milestone

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

        success, final_engine_type = run_separation_with_fallback(
            engine_type=engine_type,
            input_path=filepath,
            song_dir=song_dir,
            status_callback=lambda msg: update_progress(20, msg),
            stop_event=stop_event,
        )
        if not success:
            raise AudioProcessingError("Audio separation failed")

        from app.db.database import get_db_session
        from app.repositories.song_repository import SongRepository

        with get_db_session() as session:
            repo = SongRepository(session)
            update_kwargs: dict = {"engine_type": final_engine_type, "status": "processed"}
            try:
                update_kwargs["duration"] = librosa.get_duration(path=str(filepath))
            except Exception as e:
                logger.warning("Duration detection failed for job %s: %s", job_id, e)
            repo.update(song_id, **update_kwargs)

        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.completed_at = datetime.now()
        job_repository.update(job)
        job_repository.delete_job(job.id)

        _broadcast_job_event(job)

        celery.send_task("post_process_song", args=[song_id])
        logger.debug("Dispatched post_process_song for song %s", song_id)

        return {"status": "success", "job_id": job_id, "filename": filename}

    except audio.StopProcessingError:
        job.status = JobStatus.CANCELLED
        job.error = "Processing was manually stopped"
        job.completed_at = datetime.now()
        job_repository.update(job)
        job_repository.delete_job(job.id)
        if song_dir.exists():
            shutil.rmtree(song_dir)
        from app.db.database import get_db_session
        from app.repositories.song_repository import SongRepository

        with get_db_session() as session:
            SongRepository(session).update(song_id, status="error")
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
        job_repository.delete_job(job.id)
        from app.db.database import get_db_session
        from app.repositories.song_repository import SongRepository

        with get_db_session() as session:
            SongRepository(session).update(song_id, status="error")
        return {
            "status": "error",
            "job_id": job_id,
            "filename": filename,
            "error": error_message,
        }


@celery.task(bind=True, name="process_youtube_job", max_retries=3)
def process_youtube_job(self, job_id, video_id, metadata, engine_type="three_track"):
    """Unified task for processing YouTube videos from start to finish."""
    logger.info(
        "Starting unified YouTube processing job for job %s (artist: %s, title: %s, video_id: %s)",
        job_id,
        metadata.get("artist"),
        metadata.get("title"),
        video_id,
    )

    job_repository = JobRepository()
    job = job_repository.get_by_id(job_id)
    if not job:
        logger.error("Job %s not found for video_id %s", job_id, video_id)
        return {"status": "error", "message": "Job not found"}

    song_id = job.song_id
    if not song_id:
        logger.error("Job %s has no associated song_id", job_id)
        return {"status": "error", "message": "No song ID associated with job"}

    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    with get_db_session() as session:
        repo = SongRepository(session)
        db_song = repo.fetch(song_id)
    if not db_song:
        logger.error("Song %s not found for job %s", song_id, job_id)
        job.status = JobStatus.FAILED
        job.error = f"Song {song_id} not found in database"
        job.completed_at = datetime.now()
        job_repository.update(job)
        return {"status": "error", "message": f"Song {song_id} not found"}

    job.status = JobStatus.DOWNLOADING
    job.status_message = "Downloading video from YouTube"
    job.started_at = datetime.now()
    job.progress = 5
    job.engine_type = engine_type
    job_repository.update(job)

    celery.send_task("fetch_song_artwork", args=[song_id])
    logger.debug("[PIPELINE] ~5%% — dispatched fetch_song_artwork for song %s", song_id)

    def update_progress(progress, message, status=None):
        last_saved_progress = getattr(update_progress, "_last_saved_progress", 0)
        last_saved_status = getattr(update_progress, "_last_saved_status", None)

        job.progress = progress
        job.status_message = message
        if status:
            job.status = status

        progress_diff = abs(progress - last_saved_progress)
        status_changed = status and status != last_saved_status
        is_milestone = progress in [0, 5, 10, 12, 50, 60, 70, 73, 80, 90, 93, 95, 99, 100]
        should_save = status_changed or progress_diff >= 5 or is_milestone

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
        if progress % 25 == 0 or progress >= 95:
            logger.info("Job %s: %s%% - %s", job_id, progress, message)

    try:
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

        youtube_service.download_video(
            video_id_or_url=video_id,
            song_id=song_id,
            artist=metadata.get("artist"),
            title=metadata.get("title"),
        )

        update_progress(12, f"Download complete, preparing {engine_type} engine", JobStatus.PROCESSING)

        celery.send_task("fingerprint_single_song", args=[song_id])
        celery.send_task("detect_song_loudness", args=[song_id])
        logger.debug("[PIPELINE] ~12%% — dispatched fingerprint_single_song + detect_song_loudness for song %s", song_id)

        original_file = song_dir / "original.mp3"

        if not original_file.exists():
            raise AudioProcessingError(f"Original audio file not found: {original_file}")

        import threading

        stop_event = threading.Event()

        update_progress(12, f"Initializing {engine_type} audio processing")

        audio_progress_callback = create_audio_progress_mapper(
            engine_type=engine_type,
            base_start=12,
            base_end=50,
            update_fn=lambda prog, msg: update_progress(prog, f"Audio processing: {msg}"),
        )

        def on_vocals_ready(vocals_path: Path) -> None:
            logger.debug(
                "[PIPELINE] ~70%% — vocals.mp3 ready (%s bytes), dispatching vocal range + lyric alignment for song %s",
                vocals_path.stat().st_size if vocals_path.exists() else "missing",
                song_id,
            )
            log_lyrics_event(
                song_id,
                "vocals_ready",
                vocals_path=vocals_path,
                vocals_size_bytes=vocals_path.stat().st_size if vocals_path.exists() else None,
                pipeline_progress=70,
            )
            _create_lyrics_alignment_job(song_id, title=metadata.get("title"), artist=metadata.get("artist"))
            celery.send_task("detect_song_vocal_range", args=[song_id])
            celery.send_task("align_song_lyrics", args=[song_id])
            log_lyrics_event(song_id, "lyrics_task_dispatched", lyrics_job_id=_get_lyrics_job_id(song_id))

        success, final_engine_type = run_separation_with_fallback(
            engine_type=engine_type,
            input_path=original_file,
            song_dir=song_dir,
            status_callback=audio_progress_callback,
            stop_event=stop_event,
            on_vocals_ready=on_vocals_ready,
        )
        if not success:
            raise AudioProcessingError("Audio separation failed")

        try:
            with get_db_session() as session:
                repo = SongRepository(session)
                update_fields: dict = {"engine_type": final_engine_type, "status": "processed"}
                try:
                    update_fields["duration"] = librosa.get_duration(path=str(original_file))
                except Exception as e:
                    logger.warning("Duration detection failed for song %s: %s", song_id, e)
                repo.update(song_id, **update_fields)
        except Exception as e:
            logger.error("Error updating song metadata for song %s: %s", song_id, e)

        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.status_message = "Processing complete"
        job.completed_at = datetime.now()
        job_repository.update(job)
        job_repository.delete_job(job.id)

        _broadcast_job_event(job)

        celery.send_task("detect_song_chords", args=[song_id])
        logger.debug("[PIPELINE] ~100%% — dispatched detect_song_chords for song %s", song_id)

        return {"status": "success", "job_id": job_id, "song_id": song_id}

    except audio.StopProcessingError:
        job.status = JobStatus.CANCELLED
        job.error = "Processing was manually stopped"
        job.completed_at = datetime.now()
        job_repository.update(job)
        job_repository.delete_job(job.id)
        if song_dir.exists():
            shutil.rmtree(song_dir)
        with get_db_session() as session:
            SongRepository(session).update(song_id, status="error")
        logger.info("Job %s was cancelled", job_id)
        return {"status": "cancelled", "job_id": job_id}

    except Exception as e:
        error_message = str(e)
        logger.error("Error processing YouTube job %s: %s", job_id, error_message)
        traceback.print_exc()
        job.status = JobStatus.FAILED
        job.error = error_message
        job.completed_at = datetime.now()
        job_repository.update(job)
        job_repository.delete_job(job.id)
        with get_db_session() as session:
            SongRepository(session).update(song_id, status="error")
        return {"status": "error", "job_id": job_id, "error": error_message}
