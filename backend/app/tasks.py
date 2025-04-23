"""
Celery task definitions for audio processing
"""
from datetime import datetime
from pathlib import Path
import traceback
import shutil
from celery.utils.log import get_task_logger
from . import audio, file_management
from .celery_app import celery
from .models import JobStatus, JobStore

logger = get_task_logger(__name__)
job_store = JobStore()

class AudioProcessingError(Exception):
    """Custom exception for audio processing errors"""
    pass

@celery.task(bind=True)
def process_audio_task(self, job_id, filepath_str):
    """
    Celery task to process audio file

    Args:
        job_id: Unique identifier for the job
        filepath_str: Path to the audio file
    """
    logger.info(f"Starting audio processing task for job {job_id}")

    # Get the job from storage
    job = job_store.get_job(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return {"status": "error", "message": "Job not found"}

    filepath = Path(filepath_str)
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
        if hasattr(self, 'update_state'):
            self.update_state(
                state='PROGRESS',
                meta={
                    'job_id': job_id,
                    'filename': filename,
                    'progress': progress,
                    'status': 'processing',
                    'message': message
                }
            )
        logger.info(f"Job {job_id} progress: {progress}% - {message}")

    try:
        # Ensure library and create song directory
        file_management.ensure_library_exists()
        song_dir = file_management.get_song_dir(job_id)
        update_progress(5, f"Created directory for {job_id}")

        # Separate audio
        if not audio.separate_audio(
            filepath,
            song_dir,
            status_callback=lambda msg: update_progress(20, msg),
            stop_event=stop_event
        ):
            raise AudioProcessingError("Audio separation failed")

        # Update job status to completed
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.completed_at = datetime.now()
        job_store.save_job(job)

        return {
            "status": "success",
            "job_id": job_id,
            "filename": filename,
            "vocals_path": str(file_management.get_vocals_path_stem(song_dir).with_suffix(filepath.suffix)),
            "instrumental_path": str(file_management.get_instrumental_path_stem(song_dir).with_suffix(filepath.suffix))
        }

    except audio.StopProcessingError:
        # Processing was manually stopped
        job.status = JobStatus.CANCELLED
        job.error = "Processing was manually stopped"
        job.completed_at = datetime.now()
        job_store.save_job(job)
        if song_dir.exists():
            shutil.rmtree(song_dir)
        logger.info(f"Job {job_id} was cancelled")
        return {"status": "cancelled", "job_id": job_id, "filename": filename}

    except Exception as e:
        # Handle any other exception
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
            "error": error_message
        }

@celery.task(bind=True, name="cleanup_old_jobs")
def cleanup_old_jobs():
    """
    Periodically clean up old job records and temporary files
    """
    logger.info("Running job cleanup task")
    # Implement cleanup logic here
