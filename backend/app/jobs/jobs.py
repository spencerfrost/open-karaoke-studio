"""
Celery task definitions for audio processing
"""

from datetime import datetime
from pathlib import Path
import traceback
import shutil
from celery.utils.log import get_task_logger
from ..services import audio, file_management, FileService
from .celery_app import celery
from ..db.models import JobStatus, JobStore

logger = get_task_logger(__name__)
job_store = JobStore()


def _broadcast_job_event(job, was_created=False):
    """
    Broadcast a job event via WebSocket if available.

    Args:
        job: The job object
        was_created: Whether this is a newly created job
    """
    try:
        from ..websockets.jobs_ws import (
            broadcast_job_update,
            broadcast_job_created,
            broadcast_job_completed,
            broadcast_job_failed,
            broadcast_job_cancelled,
        )

        job_data = job.to_dict()

        # Determine the appropriate broadcast function
        if was_created:
            broadcast_job_created(job_data)
        else:
            # Map job status to appropriate event type
            if job.status == JobStatus.COMPLETED:
                broadcast_job_completed(job_data)
            elif job.status == JobStatus.FAILED:
                broadcast_job_failed(job_data)
            elif job.status == JobStatus.CANCELLED:
                broadcast_job_cancelled(job_data)
            else:
                # For PENDING, PROCESSING, or other statuses
                broadcast_job_update(job_data)

    except ImportError:
        # WebSocket not available, silently continue
        pass
    except Exception as e:
        # Log the error but don't fail the operation
        logger.warning(f"Failed to broadcast job event: {e}")


class AudioProcessingError(Exception):
    """Custom exception for audio processing errors"""

    pass


def get_filepath_from_job(job):
    """Get the full filepath for a job based on its filename"""
    from pathlib import Path
    from ..config import get_config

    # Construct the path to the original file based on the job's filename
    config = get_config()
    song_dir = Path(config.BASE_LIBRARY_DIR) / job.id
    filepath = song_dir / "original.mp3"  # Or however you determine the filename

    return str(filepath)


@celery.task(bind=True, name="process_audio_job", max_retries=3)
def process_audio_job(self, job_id):
    """
    Celery task to process audio file

    Args:
        job_id: Unique identifier for the job
    """
    logger.info(f"Starting audio processing job for job {job_id}")

    # Get the job from storage with retry logic
    job = job_store.get_job(job_id)
    if not job:
        if self.request.retries < self.max_retries:
            logger.warning(
                f"Job {job_id} not found, retrying in {2 ** self.request.retries} seconds (attempt {self.request.retries + 1}/{self.max_retries + 1})"
            )
            # Exponential backoff: 2, 4, 8 seconds
            raise self.retry(countdown=2**self.request.retries)
        else:
            logger.error(f"Job {job_id} not found after {self.max_retries + 1} attempts")
            return {"status": "error", "message": "Job not found after retries"}

    # Determine the filepath from the job
    from pathlib import Path
    from ..config import get_config

    config = get_config()
    song_dir = Path(config.BASE_LIBRARY_DIR) / job.id
    filepath = song_dir / "original.mp3"  # Or use job.filename to determine the path
    filename = filepath.name

    # Update job status to processing
    job.status = JobStatus.PROCESSING
    job.started_at = datetime.now()
    job_store.save_job(job)

    # Create a stop event (for compatibility with audio.separate_audio)
    import threading

    stop_event = threading.Event()

    def update_progress(progress, message):
        """Update job progress and log the message."""
        job.progress = progress
        job_store.save_job(job)
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
        logger.info(f"Job {job_id} progress: {progress}% - {message}")

    try:
        file_service = FileService()
        file_service.ensure_library_exists()
        song_dir = file_service.get_song_directory(job_id)
        update_progress(5, f"Created directory for {job_id}")

        # Separate audio
        if not audio.separate_audio(
            input_path=filepath,  # Pass the original MP3 file path
            song_dir=song_dir,  # Pass the song directory
            status_callback=lambda msg: update_progress(20, msg),
            stop_event=stop_event,
        ):
            raise AudioProcessingError("Audio separation failed")

        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.completed_at = datetime.now()
        job_store.save_job(job)

        _broadcast_job_event(job)

        return {
            "status": "success",
            "job_id": job_id,
            "filename": filename,
            "vocals_path": str(
                file_management.get_vocals_path_stem(song_dir).with_suffix(
                    filepath.suffix
                )
            ),
            "instrumental_path": str(
                file_management.get_instrumental_path_stem(song_dir).with_suffix(
                    filepath.suffix
                )
            ),
        }

    except audio.StopProcessingError:
        job.status = JobStatus.CANCELLED
        job.error = "Processing was manually stopped"
        job.completed_at = datetime.now()
        job_store.save_job(job)
        # Use song_dir here which is based on song_id, not job_id
        if song_dir.exists():
            shutil.rmtree(song_dir)
        logger.info(f"Job {job_id} was cancelled")
        return {"status": "cancelled", "job_id": job_id, "filename": filename}

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error processing job {job_id}: {error_message}")
        traceback.print_exc()
        job.status = JobStatus.FAILED
        job.error = error_message
        job.completed_at = datetime.now()
        job_store.save_job(job)
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


@celery.task(bind=True, name="process_youtube_job", max_retries=3)
def process_youtube_job(self, job_id, video_id, metadata):
    """
    Unified task for processing YouTube videos from start to finish

    Args:
        job_id: Job identifier
        video_id: YouTube video ID
        metadata: Dict with artist, title, album, etc.
    """
    logger.info(
        f"Starting unified YouTube processing job for job {job_id} (video_id: {video_id})"
    )

    # Get the job from storage
    job = job_store.get_job(job_id)
    if not job:
        logger.error(f"Job {job_id} not found for video_id {video_id}")
        return {"status": "error", "message": "Job not found"}

    # Get the song_id from the job
    song_id = job.song_id
    if not song_id:
        logger.error(f"Job {job_id} has no associated song_id")
        return {"status": "error", "message": "No song ID associated with job"}
        
    # Verify the song exists
    from ..db import database
    db_song = database.get_song(song_id)
    if not db_song:
        logger.error(f"Song {song_id} not found for job {job_id}")
        # Mark job as failed
        job.status = JobStatus.FAILED
        job.error = f"Song {song_id} not found in database"
        job.completed_at = datetime.now()
        job_store.save_job(job)
        return {"status": "error", "message": f"Song {song_id} not found"}

    # Update job status to downloading
    job.status = JobStatus.DOWNLOADING
    job.status_message = "Downloading video from YouTube"
    job.started_at = datetime.now()
    job.progress = 5
    job_store.save_job(job)

    def update_progress(progress, message, status=None):
        """Update job progress and status."""
        job.progress = progress
        job.status_message = message
        if status:
            job.status = status
        job_store.save_job(job)
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
        logger.info(f"Job {job_id} progress: {progress}% - {message}")

    try:
        # Phase 1: Download (5-30% progress)
        from ..services.youtube_service import YouTubeService
        from ..services.song_service import SongService

        file_service = FileService()
        file_service.ensure_library_exists()

        song_service = SongService()
        youtube_service = YouTubeService(song_service=song_service)

        update_progress(10, "Starting YouTube download")

        # Download video and extract metadata
        download_result = youtube_service.download_video(
            video_id_or_url=video_id,
            song_id=song_id,  # Use the existing song_id from the job
            artist=metadata.get("artist"),
            title=metadata.get("title"),
        )

        # Note: Song was already created in the frontend flow,
        # so we don't need to create it again here

        update_progress(
            30, "Download complete, starting audio processing", JobStatus.PROCESSING
        )

        # Phase 2: Audio Processing (30-90% progress)
        # IMPORTANT: Use song_id for the directory, not job_id
        song_dir = file_service.get_song_directory(song_id)  
        original_file = song_dir / "original.mp3"

        if not original_file.exists():
            raise AudioProcessingError(
                f"Original audio file not found: {original_file}"
            )

        # Create a stop event (for compatibility with audio.separate_audio)
        import threading

        stop_event = threading.Event()

        def audio_progress_callback(msg):
            # Map audio processing progress to 30-90% range
            current_progress = min(90, 30 + int((job.progress - 30) * 1.5))
            update_progress(current_progress, f"Audio processing: {msg}")

        # Separate audio - pass song_dir which is based on song_id
        if not audio.separate_audio(
            input_path=original_file,
            song_dir=song_dir,
            status_callback=audio_progress_callback,
            stop_event=stop_event,
        ):
            raise AudioProcessingError("Audio separation failed")

        update_progress(
            90, "Audio processing complete, finalizing", JobStatus.FINALIZING
        )

        # Phase 3: Finalization (90-100% progress)
        update_progress(95, "Cleaning up temporary files")

        # Any cleanup or final processing steps can go here

        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.status_message = "Processing complete"
        job.completed_at = datetime.now()
        job_store.save_job(job)

        _broadcast_job_event(job)

        return {
            "status": "success",
            "job_id": job_id,
            "song_id": song_id,
            "vocals_path": str(
                file_management.get_vocals_path_stem(song_dir).with_suffix(".mp3")
            ),
            "instrumental_path": str(
                file_management.get_instrumental_path_stem(song_dir).with_suffix(".mp3")
            ),
        }

    except audio.StopProcessingError:
        job.status = JobStatus.CANCELLED
        job.error = "Processing was manually stopped"
        job.completed_at = datetime.now()
        job_store.save_job(job)
        # Use song_dir here which is based on song_id, not job_id
        if song_dir.exists():
            shutil.rmtree(song_dir)
        logger.info(f"Job {job_id} was cancelled")
        return {"status": "cancelled", "job_id": job_id}

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error processing YouTube job {job_id}: {error_message}")
        traceback.print_exc()
        job.status = JobStatus.FAILED
        job.error = error_message
        job.completed_at = datetime.now()
        job_store.save_job(job)
        return {"status": "error", "job_id": job_id, "error": error_message}
