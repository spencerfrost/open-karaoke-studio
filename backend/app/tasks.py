"""
Celery task definitions for audio processing
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
import traceback
import shutil

from celery import shared_task
from celery.utils.log import get_task_logger

from . import audio
from . import file_management
from . import config
from .models import Job, JobStatus, JobStore

logger = get_task_logger(__name__)
job_store = JobStore()

class AudioProcessingError(Exception):
    """Custom exception for audio processing errors"""
    pass

@shared_task(bind=True)
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
    job.started_at = datetime.utcnow()
    job_store.save_job(job)
    
    # Create a stop event (for compatibility with audio.separate_audio)
    import threading
    stop_event = threading.Event()
    
    try:
        # Create a progress callback function for this job
        def progress_callback(message):
            # Try to extract percentage from message if available
            progress = job.progress
            if "Looking for CUDA" in message or "cuda" in message.lower():
                # The "Looking for CUDA" message comes at around 5%
                progress = 5
            elif "separating" in message.lower():
                # This happens during separation, around 10-20%
                progress = 20
            elif "saving" in message.lower():
                # Final stages
                progress = 90
            elif "%" in message:
                try:
                    progress_str = message.split("%")[0].split(" ")[-1].strip()
                    progress = int(float(progress_str))
                except (ValueError, IndexError):
                    pass
            
            # Update job progress
            job.progress = progress
            job_store.save_job(job)
            
            # Also update Celery task state if running as a Celery task
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
            
        # 1. Ensure library and create song directory
        file_management.ensure_library_exists()
        song_dir = file_management.get_song_dir(filepath)
        progress_callback(f"Created directory for {filename}")
        
        # 2. Copy original file
        original_saved_path = file_management.save_original_file(filepath, song_dir)
        if not original_saved_path:
            raise AudioProcessingError("Failed to copy original file")
        progress_callback("Copied original file")
        
        # 3. Separate audio
        if not audio.separate_audio(
            filepath, 
            song_dir, 
            status_callback=progress_callback, 
            stop_event=stop_event
        ):
            raise AudioProcessingError("Audio separation failed")
            
        # 4. Update job status to completed
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.completed_at = datetime.utcnow()
        job_store.save_job(job)
        
        # 5. Return success result
        result = {
            "status": "success",
            "job_id": job_id,
            "filename": filename,
            "vocals_path": str(file_management.get_vocals_path_stem(song_dir).with_suffix(filepath.suffix)),
            "instrumental_path": str(file_management.get_instrumental_path_stem(song_dir).with_suffix(filepath.suffix))
        }
        logger.info(f"Job {job_id} completed successfully")
        return result
        
    except audio.StopProcessingError:
        # Processing was manually stopped
        job.status = JobStatus.CANCELLED
        job.error = "Processing was manually stopped"
        job.completed_at = datetime.utcnow()
        job_store.save_job(job)
        
        # Clean up partial files
        if song_dir.exists():
            shutil.rmtree(song_dir)
            
        logger.info(f"Job {job_id} was cancelled")
        return {"status": "cancelled", "job_id": job_id, "filename": filename}
        
    except Exception as e:
        # Handle any other exception
        error_message = str(e)
        logger.error(f"Error processing job {job_id}: {error_message}")
        traceback.print_exc()
        
        # Update job status
        job.status = JobStatus.FAILED
        job.error = error_message
        job.completed_at = datetime.utcnow()
        job_store.save_job(job)
        
        return {
            "status": "error", 
            "job_id": job_id, 
            "filename": filename,
            "error": error_message
        }

@shared_task
def cleanup_old_jobs():
    """
    Periodically clean up old job records and temporary files
    """
    # Implement cleanup logic here
    logger.info("Running job cleanup task")
    # This could delete jobs older than X days or remove temporary files
    pass
