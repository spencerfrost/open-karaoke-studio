from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS  # For handling CORS
from pathlib import Path
from typing import List, Optional, Dict, Any
from werkzeug.utils import secure_filename
import os
import traceback
import uuid
from datetime import datetime, timedelta
from functools import wraps

# Import app modules using relative imports
from . import audio, file_management, config
from .celery_app import make_celery
from .models import Job, JobStatus, JobStore
from .tasks import process_audio_task

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes (adjust as needed for production)

# Setup Celery
celery = make_celery(app)

# Initialize the job store
job_store = JobStore()

# --- Configuration ---
UPLOAD_FOLDER = config.YT_DOWNLOAD_DIR  # Use the download directory for uploads
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB limit (adjust as needed)

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# --- Data Models ---
class Song(object):  # Simplified - adjust as needed
    def __init__(self, id: str, title: str, artist: str):
        self.id = id
        self.title = title
        self.artist = artist


# --- Error Handling ---
class ProcessingError(Exception):
    """Custom exception for processing errors."""

    def __init__(self, message, status_code=500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@app.errorhandler(ProcessingError)
def handle_processing_error(error):
    response = jsonify({"error": error.message})
    response.status_code = error.status_code
    return response


# --- Helper Functions ---
def allowed_file(filename):
    """Checks if the file extension is allowed."""
    ALLOWED_EXTENSIONS = {
        ".mp3",
        ".wav",
        ".flac",
        ".ogg",
        ".m4a",
    }  # Consider moving to config
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


# --- Fallback Processing ---
def run_audio_processing_directly(job_id: str, filepath_str: str):
    """Run audio processing directly in a thread (fallback when Celery is unavailable)"""
    from .tasks import process_audio_task
    
    # We're calling the task function directly, not through Celery
    # It expects 'self' as first arg for @shared_task with bind=True
    class DummyTask:
        def update_state(self, state=None, meta=None):
            pass  # No-op for direct execution
    
    dummy_task = DummyTask()
    
    try:
        # Call the task function directly with the dummy task as 'self'
        process_audio_task(dummy_task, job_id, filepath_str)
    except Exception as e:
        print(f"Error in direct processing: {e}")
        import traceback
        traceback.print_exc()


# --- Queue Management Functions ---
def create_job(filename: str) -> Job:
    """Create a new job for audio processing"""
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        filename=filename,
        status=JobStatus.PENDING,
        created_at=datetime.utcnow()
    )
    job_store.save_job(job)
    return job

def start_processing_job(job: Job, filepath: Path) -> Dict[str, Any]:
    """Start a Celery task for audio processing"""
    try:
        task = process_audio_task.delay(job.id, str(filepath))
        return {
            "job_id": job.id,
            "filename": job.filename,
            "status": job.status.value,
            "task_id": task.id
        }
    except Exception as e:
        # Log the error
        print(f"Error starting Celery task: {e}")
        
        # Fall back to processing in the main process
        print("Warning: Celery unavailable, processing in main thread")
        
        # Update job status to indicate direct processing
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        job_store.save_job(job)
        
        # Start processing in a thread instead (non-blocking but not distributed)
        import threading
        thread = threading.Thread(
            target=run_audio_processing_directly,
            args=(job.id, str(filepath)),
            daemon=True
        )
        thread.start()
        
        return {
            "job_id": job.id,
            "filename": job.filename,
            "status": job.status.value,
            "direct_processing": True  # Indicate we're not using Celery
        }


# --- API Endpoints ---
@app.route("/process", methods=["POST"])
def process_audio():
    """Endpoint to initiate audio processing."""

    if "audio_file" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio_file"]

    if audio_file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if audio_file and allowed_file(audio_file.filename):
        filename = secure_filename(audio_file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        try:
            audio_file.save(filepath)
        except Exception as e:
            return jsonify({"error": f"Error saving file: {e}"}), 500

        # Create a new job and start processing
        job = create_job(filename)
        result = start_processing_job(job, Path(filepath))
        
        # Get queue position
        pending_jobs = job_store.get_jobs_by_status(JobStatus.PENDING)
        position_in_queue = len(pending_jobs)
        
        return (
            jsonify({
                "message": "Processing queued",
                "job_id": job.id,
                "filename": filename,
                "position_in_queue": position_in_queue
            }),
            202,
        )  # Accepted
    else:
        return jsonify({"error": "Invalid file type"}), 400


@app.route("/status/<filename>", methods=["GET"])
def get_processing_status(filename):
    """Endpoint to get the status of an audio processing task by filename."""
    
    # Try to find job by filename
    matching_jobs = [j for j in job_store.get_all_jobs() if j.filename == filename]
    
    if not matching_jobs:
        # Legacy check for processed files
        song_dir = file_management.get_song_dir(Path(filename))
        vocals_path = file_management.get_vocals_path_stem(song_dir).with_suffix(".wav")  # Or other extension
        instrumental_path = file_management.get_instrumental_path_stem(song_dir).with_suffix(".wav")
        
        if vocals_path.exists() and instrumental_path.exists():
            return jsonify({
                "status": "success",
                "vocals_path": str(vocals_path),
                "instrumental_path": str(instrumental_path),
            })
        else:
            return jsonify({"status": "not_found"})
    
    # Return the most recent job for this filename
    job = sorted(matching_jobs, key=lambda j: j.created_at, reverse=True)[0]
    
    response = {
        "status": job.status.value,
        "job_id": job.id,
        "filename": job.filename,
        "progress": job.progress
    }
    
    # Add additional info based on status
    if job.status == JobStatus.COMPLETED:
        song_dir = file_management.get_song_dir(Path(filename))
        vocals_path = file_management.get_vocals_path_stem(song_dir).with_suffix(".mp3")  # Assuming mp3
        instrumental_path = file_management.get_instrumental_path_stem(song_dir).with_suffix(".mp3")
        
        response.update({
            "vocals_path": str(vocals_path),
            "instrumental_path": str(instrumental_path)
        })
    elif job.status == JobStatus.FAILED:
        response["error"] = job.error
    
    return jsonify(response)


@app.route("/songs", methods=["GET"])
def get_songs():
    """Endpoint to get a list of processed songs."""
    songs = []
    for song_dir in file_management.get_processed_songs():
        # Basic song info - you might want to store more metadata
        songs.append(Song(id=song_dir, title=song_dir, artist="Unknown"))
    return jsonify([song.__dict__ for song in songs])


@app.route("/download/<path:filename>", methods=["GET"])
def download_file(filename):
    """Endpoint to download a processed file."""

    # Determine if it's vocals or instrumental (crude method, improve this)
    if "vocals" in filename:
        directory = file_management.get_song_dir(Path(filename).with_suffix(""))
        return send_from_directory(directory, filename)
    elif "instrumental" in filename:
        directory = file_management.get_song_dir(Path(filename).with_suffix(""))
        return send_from_directory(directory, filename)
    else:
        return jsonify({"error": "Invalid filename for download"}), 400


# --- Queue API Endpoints ---
@app.route("/queue/status", methods=["GET"])
def get_queue_status():
    """Get the overall status of the processing queue"""
    stats = job_store.get_stats()
    return jsonify(stats)

@app.route("/queue/jobs", methods=["GET"])
def get_queue_jobs():
    """List all jobs in the queue with their status"""
    status_filter = request.args.get("status", None)
    
    if status_filter:
        try:
            status = JobStatus(status_filter)
            jobs = job_store.get_jobs_by_status(status)
        except ValueError:
            return jsonify({"error": f"Invalid status: {status_filter}"}), 400
    else:
        jobs = job_store.get_all_jobs()
    
    # Sort jobs by created_at (newest first)
    jobs = sorted(jobs, key=lambda j: j.created_at, reverse=True)
    
    return jsonify({
        "jobs": [job.to_dict() for job in jobs]
    })

@app.route("/queue/job/<job_id>", methods=["GET"])
def get_queue_job(job_id):
    """Get detailed information about a specific job"""
    job = job_store.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    response = job.to_dict()
    
    # Add additional info for completed jobs
    if job.status == JobStatus.COMPLETED:
        song_dir = file_management.get_song_dir(Path(job.filename))
        vocals_path = file_management.get_vocals_path_stem(song_dir).with_suffix(".mp3")  # Assuming mp3
        instrumental_path = file_management.get_instrumental_path_stem(song_dir).with_suffix(".mp3")
        
        response.update({
            "vocals_path": str(vocals_path),
            "instrumental_path": str(instrumental_path)
        })
    
    # Estimate completion time if processing
    if job.status == JobStatus.PROCESSING and job.started_at:
        if job.progress > 0:
            elapsed_time = (datetime.utcnow() - job.started_at).total_seconds()
            if elapsed_time > 0:
                # Estimate based on current progress
                time_per_percent = elapsed_time / job.progress
                remaining_percent = 100 - job.progress
                estimated_remaining = remaining_percent * time_per_percent
                
                estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_remaining)
                response["expected_completion"] = estimated_completion.isoformat()
    
    return jsonify(response)

@app.route("/queue/job/<job_id>/cancel", methods=["POST"])
def cancel_queue_job(job_id):
    """Cancel a pending or in-progress job"""
    job = job_store.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        return jsonify({"error": f"Cannot cancel job with status {job.status}"}), 400
    
    # Update job status
    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.utcnow()
    job.error = "Cancelled by user"
    job_store.save_job(job)
    
    # TODO: Implement actual task cancellation in Celery
    # This would involve celery.control.revoke(task_id, terminate=True)
    
    return jsonify({
        "success": True,
        "message": "Job cancelled",
        "job_id": job_id
    })


if __name__ == "__main__":
    # Make sure required directories exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)
