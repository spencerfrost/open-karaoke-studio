# backend/app/main.py

# --- Imports ---
from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
from werkzeug.utils import secure_filename
import os
import traceback
import uuid  # For job IDs
from datetime import datetime  # For job creation time
import logging  # For logging
from typing import Dict, Any  # For type hinting

# --- Import App Modules ---
# Use absolute imports assuming 'app' is the package root or PYTHONPATH is set
from app import audio, file_management, config  # Core logic
from app.celery_app import make_celery  # Celery app factory
from app.models import (
    Job,
    JobStatus,
    JobStore,
)  # Job/Data models (ensure JobStore is defined correctly)
from app.tasks import process_audio_task  # Celery task import

# --- Import Blueprints ---
from app.song_endpoints import song_bp  # Song API blueprint
from app.queue_endpoints import queue_bp  # Queue API blueprint

# --- App Setup ---
app = Flask(__name__)
CORS(app)  # Configure CORS appropriately for production

# Configure Logging
logging.basicConfig(level=logging.INFO)  # Basic config, adjust as needed
app.logger.setLevel(logging.INFO)  # Ensure Flask logger uses the level

# Setup Celery - Pass the Flask app instance
celery = make_celery(app)

# Initialize the Job Store (ensure JobStore() implementation exists and works)
# This might handle loading/saving jobs from files or a database
try:
    job_store = JobStore()
    app.logger.info("JobStore initialized.")
except Exception as e:
    app.logger.error(f"Failed to initialize JobStore: {e}", exc_info=True)
    # Depending on JobStore importance, might exit or continue with limited functionality
    job_store = None  # Or a dummy store

# --- Configuration ---
UPLOAD_FOLDER = config.YT_DOWNLOAD_DIR
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB limit
# Ensure upload directory exists
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except OSError as e:
    app.logger.error(
        f"Could not create upload folder {UPLOAD_FOLDER}: {e}", exc_info=True
    )


# --- Error Handling ---
class ProcessingError(Exception):
    """Custom error for processing issues handled gracefully."""

    def __init__(self, message, status_code=500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@app.errorhandler(ProcessingError)
def handle_processing_error(error):
    app.logger.warning(
        f"Processing Error: {error.message} (Status Code: {error.status_code})"
    )
    response = jsonify({"error": error.message})
    response.status_code = error.status_code
    return response


@app.errorhandler(Exception)
def handle_generic_error(error):
    """Catch-all for unexpected errors."""
    app.logger.error(f"Unhandled Exception: {error}", exc_info=True)
    response = jsonify(
        {"error": "An unexpected server error occurred. Please check logs."}
    )
    response.status_code = 500
    return response


# --- Helper Functions ---
def allowed_file(filename: str) -> bool:
    """Checks if the file extension is allowed."""
    ALLOWED_EXTENSIONS = {
        ".mp3",
        ".wav",
        ".flac",
        ".ogg",
        ".m4a",
    }  # Consider moving to config
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


# --- Fallback Processing (if Celery fails) ---
def run_audio_processing_directly(job_id: str, filepath_str: str):
    """
    Runs audio processing directly in a thread (fallback).
    NOTE: This bypasses the Celery queue and runs locally. Not recommended for production.
    """
    app.logger.warning(f"Running job {job_id} directly in fallback thread.")
    # Need app context if task uses Flask features
    with app.app_context():
        # We're calling the task function directly, not through Celery
        # It expects 'self' as first arg for @shared_task with bind=True
        class DummyTask:
            def update_state(self, state=None, meta=None):
                # Log progress locally instead of updating Celery state
                if meta:
                    progress = meta.get("progress", "?")
                    message = meta.get("message", "")
                    app.logger.info(
                        f"[DirectRun-{job_id}] Progress: {progress}% - {message}"
                    )
                else:
                    app.logger.info(f"[DirectRun-{job_id}] State: {state}")

            # Add request attribute if needed by context task base class
            # request = None

        dummy_task = DummyTask()
        try:
            # Call the task function directly with the dummy task as 'self'
            process_audio_task(dummy_task, job_id, filepath_str)
            app.logger.info(f"Direct processing finished for job {job_id}.")
        except Exception as e:
            app.logger.error(
                f"Error during direct processing for job {job_id}: {e}", exc_info=True
            )
            # Update JobStore status if possible
            if job_store:
                try:
                    job = job_store.get_job(job_id)
                    if job:
                        job.status = JobStatus.FAILED
                        job.error = f"Direct processing failed: {str(e)}"
                        job.completed_at = datetime.utcnow()
                        job_store.save_job(job)
                except Exception as store_err:
                    app.logger.error(
                        f"Failed to update JobStore after direct processing error: {store_err}"
                    )


# --- Queue Management Functions ---
def create_job(filename: str) -> Job | None:
    """Creates and stores a new job record."""
    if not job_store:
        app.logger.error("JobStore not available, cannot create job.")
        return None
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        filename=filename,
        status=JobStatus.PENDING,
        created_at=datetime.utcnow(),
    )
    try:
        job_store.save_job(job)
        app.logger.info(f"Created Job {job_id} for file {filename}")
        return job
    except Exception as e:
        app.logger.error(f"Failed to save new job {job_id}: {e}", exc_info=True)
        return None


def start_processing_job(job: Job, filepath: Path) -> Dict[str, Any]:
    """Starts a Celery task for audio processing, with fallback."""
    app.logger.info(f"Attempting to start processing for Job {job.id} via Celery.")
    try:
        # Send task to Celery queue
        task = process_audio_task.delay(job.id, str(filepath))
        app.logger.info(f"Successfully queued Celery task {task.id} for Job {job.id}")
        # Update Job with Celery Task ID (optional but useful)
        job.task_id = task.id
        job_store.save_job(job)
        return {
            "job_id": job.id,
            "filename": job.filename,
            "status": job.status.value,  # Should still be PENDING initially
            "task_id": task.id,
        }
    except Exception as e:  # Catch specific Celery connection errors if possible
        app.logger.error(
            f"CRITICAL: Error starting Celery task for Job {job.id}: {e}", exc_info=True
        )
        app.logger.warning(
            "Attempting fallback: processing directly in main process thread."
        )

        # Update job status to indicate direct processing attempt
        job.status = JobStatus.PROCESSING  # Mark as processing directly
        job.started_at = datetime.utcnow()
        job.notes = "Processing directly due to Celery dispatch failure."  # Add note
        job_store.save_job(job)

        # Start processing in a separate thread (non-blocking but runs locally)
        import threading

        thread = threading.Thread(
            target=run_audio_processing_directly,
            args=(job.id, str(filepath)),
            daemon=True,  # Allows app to exit even if thread is running
        )
        thread.start()
        app.logger.info(f"Started fallback processing thread for Job {job.id}")

        return {
            "job_id": job.id,
            "filename": job.filename,
            "status": job.status.value,  # Now PROCESSING
            "direct_processing": True,  # Indicate fallback was used
        }


# --- API Endpoints ---


@app.route("/process", methods=["POST"])
def process_audio_endpoint():
    """Endpoint to upload audio and queue it for processing."""
    app.logger.info("Received request for /process endpoint.")
    if "audio_file" not in request.files:
        app.logger.warning("'/process' request missing 'audio_file' part.")
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio_file"]
    if not audio_file or audio_file.filename == "":
        app.logger.warning("'/process' request received empty file.")
        return jsonify({"error": "No file selected"}), 400

    if allowed_file(audio_file.filename):
        filename = secure_filename(
            str(audio_file.filename)
        )  # Ensure filename is safe string
        filepath = Path(app.config["UPLOAD_FOLDER"]) / filename
        app.logger.info(f"Processing uploaded file: {filename}")

        try:
            # Ensure upload folder exists (redundant if done at start, but safe)
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            audio_file.save(filepath)
            app.logger.info(f"File saved successfully: {filepath}")
        except Exception as e:
            app.logger.error(
                f"Error saving uploaded file '{filename}': {e}", exc_info=True
            )
            return jsonify({"error": f"Error saving uploaded file: {e}"}), 500

        # Create a new job record
        job = create_job(filename)
        if not job:
            # Error already logged by create_job
            return jsonify({"error": "Failed to create processing job record."}), 500

        # Attempt to start the processing job (Celery or fallback)
        result = start_processing_job(job, filepath)

        # Calculate approximate queue position (only counts PENDING jobs)
        position_in_queue = -1  # Default if store unavailable or error
        if job_store:
            try:
                pending_jobs = job_store.get_jobs_by_status(JobStatus.PENDING)
                # Find the index of our job ID among pending ones
                pending_ids = [p.id for p in pending_jobs]
                try:
                    position_in_queue = pending_ids.index(job.id) + 1  # 1-based index
                except ValueError:
                    # Job might already be processing if fallback happened quickly
                    if job.status == JobStatus.PROCESSING:
                        position_in_queue = 0  # Indicate it's actively processing
                    else:
                        position_in_queue = (
                            len(pending_ids) + 1
                        )  # Append to end conceptually
            except Exception as q_err:
                app.logger.error(
                    f"Could not determine queue position: {q_err}", exc_info=True
                )

        # Return Job ID and status to the client
        # Use 202 Accepted status code
        response_data = {
            "message": (
                "Processing job created and queued"
                if not result.get("direct_processing")
                else "Processing job created (direct fallback)"
            ),
            "job_id": job.id,
            "filename": filename,
            "status": job.status.value,
            "task_id": result.get("task_id"),  # Include Celery task ID if available
            "position_in_queue": position_in_queue,
        }
        return jsonify(response_data), 202

    else:
        app.logger.warning(
            f"'/process' request received invalid file type: {audio_file.filename}"
        )
        return jsonify({"error": "Invalid file type"}), 400


# --- Register Blueprints ---
app.register_blueprint(song_bp)
app.logger.info("Registered song_bp blueprint at /api/songs")
app.register_blueprint(queue_bp)
app.logger.info("Registered queue_bp blueprint at /queue")


# --- Main Guard ---
if __name__ == "__main__":
    app.logger.info("Starting Flask development server...")
    # Use host='0.0.0.0' to be accessible on the network
    # Turn off Flask reloader if using Celery worker in same env to avoid issues
    use_reloader = os.environ.get("FLASK_USE_RELOADER", "true").lower() == "true"
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=use_reloader)
