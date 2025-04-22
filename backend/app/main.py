# backend/app/main.py
from flask import Flask, request, jsonify
from . import youtube
from flask_cors import CORS
from pathlib import Path
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
import logging
from typing import Dict, Any

from . import config
from .celery_app import init_celery, celery
from .tasks import process_audio_task
from .models import (
    Job,
    JobStatus,
    JobStore,
)
from .song_endpoints import song_bp
from .queue_endpoints import queue_bp

# --- Flask app Setup ---
app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"], supports_credentials=True)

# --- Configuration FIRST ---
app.config.from_object(config)
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app.config["UPLOAD_FOLDER"] = config.YT_DOWNLOAD_DIR
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# --- Celery Initialization ---
init_celery(app)
try:
    job_store = JobStore()
    app.logger.info("JobStore instance created successfully.")
except Exception as e:
    app.logger.error(f"Failed to initialize JobStore: {e}", exc_info=True)
    job_store = None


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
        created_at=datetime.now(),
    )
    try:
        job_store.save_job(job)
        app.logger.info(f"Created Job {job_id} for file {filename}")
        return job
    except Exception as e:
        app.logger.error(f"Failed to save new job {job_id}: {e}", exc_info=True)
        return None


def start_processing_job(job: Job, filepath: Path) -> Dict[str, Any]:
    """Starts a Celery task for audio processing."""
    app.logger.info(f"Attempting to start processing for Job {job.id} via Celery.")
    app.logger.info(f"Using Celery Broker: {celery.conf.broker_url}")

    # --- Direct Redis Ping Test (Optional but Recommended) ---
    # (Keep the ping test using redis.ConnectionPool.from_url(celery.conf.broker_url) as before)
    # ...

    # Send task to Celery queue using the IMPORTED 'celery' instance
    try:
        # Make sure process_audio_task is decorated with the SAME celery instance
        task = process_audio_task.delay(job.id, str(filepath))
        app.logger.info(f"Celery task dispatched successfully. Task ID: {task.id}")
    except Exception as celery_err:
        app.logger.error(f"Celery .delay() FAILED: {celery_err}", exc_info=True)
        # Check traceback carefully here in logs!
        raise ProcessingError(f"Failed to queue processing task: {celery_err}", 500)

    job.task_id = task.id
    job.status = JobStatus.PENDING
    job_store.save_job(job)

    return {
        "job_id": job.id,
        "filename": job.filename,
        "status": job.status.value,
        "task_id": task.id,
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

@app.route('/api/youtube/search', methods=['POST'])
def search_youtube_route():
    data = request.json
    query = data.get('query', '')
    max_results = data.get('max_results', 10)

    if not query:
        return jsonify({'error': 'Query is required'}), 400

    try:
        results = youtube.search_youtube(query, max_results)
        return jsonify({'results': results})
    except Exception as e:
        app.logger.error(f"YouTube search error: {str(e)}")
        return jsonify({'error': f'Failed to search YouTube: {str(e)}'}), 500

@app.route('/api/youtube/download', methods=['POST'])
def download_youtube_route():
    data = request.json
    video_id = data.get('video_id', '')

    if not video_id:
        return jsonify({'error': 'Video ID is required'}), 400

    try:
        upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
        result = youtube.download_youtube_audio(video_id, upload_folder)

        # Return info including the processing job details
        response_data = {
            'success': True,
            'file': result['filepath'],
            'metadata': {
                'id': result['id'],
                'title': result['title'],
                'duration': result['duration'],
                'uploader': result['uploader']
            },
            'processing': {
                'job_id': result['job_id'],
                'status': result['job_status'],
                'task_id': result['task_id']
            }
        }
        return jsonify(response_data), 202
    except Exception as e:
        app.logger.error(f"YouTube download error: {str(e)}")
        return jsonify({'error': f'Failed to download from YouTube: {str(e)}'}), 500

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
