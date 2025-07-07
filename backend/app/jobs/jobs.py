"""
Celery task definitions for audio processing
"""

import shutil
import traceback
from datetime import datetime

from celery.utils.log import get_task_logger

from ..config.logging import get_structured_logger
from ..db.models import JobStatus
from ..repositories import JobRepository
from ..services import FileService, audio, file_management
from .celery_app import celery

logger = get_task_logger(__name__)
# Add structured logging for better job tracking
structured_logger = get_structured_logger(
    "app.jobs", {"module": "jobs", "component": "task_processor"}
)
job_repository = JobRepository()


def _broadcast_job_event(job, was_created=False):
    """
    Broadcast a job event via WebSocket if available.

    Args:
        job: The job object
        was_created: Whether this is a newly created job
    """
    try:
        from ..websockets.jobs_ws import (
            broadcast_job_cancelled,
            broadcast_job_completed,
            broadcast_job_created,
            broadcast_job_failed,
            broadcast_job_update,
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
        logger.warning("Failed to broadcast job event: %s", e)


class AudioProcessingError(Exception):
    """Custom exception for audio processing errors"""


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

    from ..config import get_config

    config = get_config()
    song_dir = Path(config.BASE_LIBRARY_DIR) / job.id
    filepath = song_dir / "original.mp3"  # Or use job.filename to determine the path
    filename = filepath.name

    # Update job status to processing
    job.status = JobStatus.PROCESSING
    job.started_at = datetime.now()
    job_repository.update(job)

    # Create a stop event (for compatibility with audio.separate_audio)
    import threading

    stop_event = threading.Event()

    def update_progress(progress, message):
        """Update job progress and log the message."""
        job.progress = progress
        job_repository.update(job)
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
        # Enhanced logging with structured data
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
        logger.info("Job %s progress: %s% - %s", job_id, progress, message)

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
        job_repository.update(job)

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
        "Starting unified YouTube processing job for job %s (video_id: %s)",
        job_id,
        video_id,
    )

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
    from ..db.database import get_db_session
    from ..repositories.song_repository import SongRepository

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
    job_repository.update(job)

    def update_progress(progress, message, status=None):
        """Update job progress and status."""
        job.progress = progress
        job.status_message = message
        if status:
            job.status = status
        job_repository.update(job)
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
        from ..services.youtube_service import YouTubeService

        file_service = FileService()
        file_service.ensure_library_exists()

        youtube_service = YouTubeService()

        update_progress(10, "Starting YouTube download")

        # Download video and extract metadata
        download_result = youtube_service.download_video(
            video_id_or_url=video_id,
            song_id=song_id,  # Use the existing song_id from the job
            artist=metadata.get("artist"),
            title=metadata.get("title"),
        )

        # Extract enhanced metadata from download result
        _, enhanced_metadata = download_result

        # Get song directory for file paths
        song_dir = file_service.get_song_directory(song_id)

        # Update the database song with enhanced metadata (including iTunes data)
        try:
            from ..db.database import get_db_session
            from ..repositories.song_repository import SongRepository

            with get_db_session() as session:
                repo = SongRepository(session)
                update_fields = {
                    "title": enhanced_metadata.get("title") or db_song.title,
                    "artist": enhanced_metadata.get("artist") or db_song.artist,
                    "duration_ms": enhanced_metadata.get("duration_ms"),
                    "album": enhanced_metadata.get("album") or db_song.album,
                    "genre": enhanced_metadata.get("genre") or db_song.genre,
                    "year": enhanced_metadata.get("year") or db_song.year,
                    "lyrics": enhanced_metadata.get("lyrics") or db_song.lyrics,
                    # add more fields as needed
                }
                updated_song = repo.update(song_id, **update_fields)
                if updated_song:
                    logger.info(
                        "Successfully updated song %s with enhanced metadata", song_id
                    )
                    update_progress(25, "Enhanced metadata saved")
                else:
                    logger.warning(
                        "Failed to update song %s with enhanced metadata", song_id
                    )

            # Success/failure handling is now above using updated_song

        except Exception as e:
            logger.error("Error updating song metadata for %s: %s", song_id, e)
            # Continue processing even if metadata update fails

        update_progress(
            30, "Download complete, starting audio processing", JobStatus.PROCESSING
        )

        # Phase 2: Audio Processing (30-90% progress)
        # IMPORTANT: Use song_id for the directory, not job_id
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
        update_progress(93, "Downloading thumbnail")

        # Phase 3A: Download thumbnail (separate from stepper-sensitive operations)
        try:
            thumbnail_url = youtube_service.fetch_and_save_thumbnail(video_id, song_id)
            if thumbnail_url:
                update_progress(95, "Thumbnail download complete")
            else:
                update_progress(95, "Thumbnail download failed, continuing")
        except Exception as e:
            # Thumbnail failures should not break the job
            logger.warning("Thumbnail download failed for %s: %s", video_id, e)
            update_progress(95, "Thumbnail download failed, continuing")

        update_progress(99, "Finalizing processing")

        # Phase 1A Task 3: Update database with audio file paths after processing
        try:
            vocals_path = file_management.get_vocals_path_stem(song_dir).with_suffix(
                ".mp3"
            )
            instrumental_path = file_management.get_instrumental_path_stem(
                song_dir
            ).with_suffix(".mp3")

            # Verify the files actually exist before updating database
            if vocals_path.exists() and instrumental_path.exists():
                # Get relative paths from library directory
                from ..config import get_config

                config = get_config()

                vocals_relative = str(vocals_path.relative_to(config.LIBRARY_DIR))
                instrumental_relative = str(
                    instrumental_path.relative_to(config.LIBRARY_DIR)
                )

                with get_db_session() as session:
                    repo = SongRepository(session)
                    update_fields = {
                        "vocals_path": vocals_relative,
                        "instrumental_path": instrumental_relative,
                        "processing_status": "completed",
                        "has_audio_files": True,
                    }
                    updated_song = repo.update(song_id, **update_fields)
                    success = updated_song is not None

                if not success:
                    logger.warning("Failed to update audio paths for song %s", song_id)
            else:
                logger.warning(
                    "Audio files not found after processing for song %s", song_id
                )

        except Exception as e:
            # Don't fail the job for path update issues, just log the error
            logger.error("Error updating audio paths for song %s: %s", song_id, e)

        # Any cleanup or final processing steps can go here

        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.status_message = "Processing complete"
        job.completed_at = datetime.now()
        job_repository.update(job)

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
        job_repository.update(job)
        # Use song_dir here which is based on song_id, not job_id
        if song_dir.exists():
            shutil.rmtree(song_dir)
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
        return {"status": "error", "job_id": job_id, "error": error_message}


# Event system integration
def _handle_job_event(event):
    """
    Handle job events from the event system.

    This replaces the direct function calls from models.
    """
    try:
        from ..db.models import Job, JobStatus
        from ..utils.events import JobEvent

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
        from ..utils.events import subscribe_to_job_events

        subscribe_to_job_events(_handle_job_event)
        logger.info("Jobs module subscribed to job events")
    except Exception as e:
        logger.error("Failed to set up job event subscriptions: %s", e)


# Set up subscriptions when module loads
_setup_event_subscriptions()
