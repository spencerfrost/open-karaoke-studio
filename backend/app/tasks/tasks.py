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

@celery.task(bind=True, name='process_audio_task', max_retries=3)
def process_audio_task(self, job_id):
    """
    Celery task to process audio file
    
    Args:
        job_id: Unique identifier for the job
    """
    logger.info(f"Starting audio processing task for job {job_id}")
    
    # Get the job from storage with retry logic
    job = job_store.get_job(job_id)
    if not job:
        if self.request.retries < self.max_retries:
            logger.warning(f"Job {job_id} not found, retrying in {2 ** self.request.retries} seconds")
            # Exponential backoff: 2, 4, 8 seconds
            raise self.retry(countdown=2 ** self.request.retries)
        else:
            logger.error(f"Job {job_id} not found after {self.max_retries} retries")
            return {"status": "error", "message": "Job not found"}
    
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
        file_service = FileService()
        file_service.ensure_library_exists()
        song_dir = file_service.get_song_directory(job_id)
        update_progress(5, f"Created directory for {job_id}")

        # Separate audio
        if not audio.separate_audio(
            input_path=filepath,  # Pass the original MP3 file path
            song_dir=song_dir,    # Pass the song directory
            status_callback=lambda msg: update_progress(20, msg),
            stop_event=stop_event
        ):
            raise AudioProcessingError("Audio separation failed")

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
        job.status = JobStatus.CANCELLED
        job.error = "Processing was manually stopped"
        job.completed_at = datetime.now()
        job_store.save_job(job)
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
            "error": error_message
        }

@celery.task(bind=True, name='cleanup_old_jobs')
def cleanup_old_jobs(self):
    """
    Periodically clean up old job records and temporary files
    """
    logger.info("Running job cleanup task")
    # Implement cleanup logic here
