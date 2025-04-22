from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS  # For handling CORS
from pathlib import Path
from typing import List, Optional
from werkzeug.utils import secure_filename
import os
import threading
import shutil
import traceback
from functools import wraps

import audio
import file_management
import config

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes (adjust as needed for production)

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


# --- Background Task Management ---
# In a real production environment, consider using a proper task queue
# like Celery. This is a simplified in-memory approach for demonstration.

processing_threads = {}  # Store threads, keyed by a unique ID (e.g., filename)
stop_events = {}


def start_background_processing(filepath: Path, filename: str):
    """Starts the audio processing in a background thread."""

    def process_in_thread(filepath: Path, filename: str):
        try:
            stop_event = threading.Event()
            stop_events[filename] = stop_event

            # 1. Ensure library and create song directory
            file_management.ensure_library_exists()
            song_dir = file_management.get_song_dir(filepath)

            # 2. Copy original file
            original_saved_path = file_management.save_original_file(filepath, song_dir)
            if not original_saved_path:
                raise ProcessingError("Failed to copy original file.", 500)

            # 3. Separate audio
            if not audio.separate_audio(
                filepath, song_dir, status_callback=None, stop_event=stop_event
            ):
                raise ProcessingError("Audio separation failed.", 500)

        except audio.StopProcessingError:
            print(f"Processing stopped for {filename}")
            # Clean up partial files (optional)
            if song_dir.exists():
                shutil.rmtree(song_dir)
        except Exception as e:
            print(f"Error during processing: {e}")
            traceback.print_exc()
            raise ProcessingError(f"Processing error: {e}", 500)
        finally:
            processing_threads.pop(filename, None)  # Clean up thread reference
            stop_events.pop(filename, None)

    thread = threading.Thread(target=process_in_thread, args=(filepath, filename))
    processing_threads[filename] = thread
    thread.start()


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

        start_background_processing(Path(filepath), filename)
        return (
            jsonify({"message": "Processing started", "filename": filename}),
            202,
        )  # Accepted
    else:
        return jsonify({"error": "Invalid file type"}), 400


@app.route("/status/<filename>", methods=["GET"])
def get_processing_status(filename):
    """Endpoint to get the status of an audio processing task."""

    if filename in processing_threads:
        return jsonify({"status": "processing"})
    elif filename in stop_events:
        return jsonify({"status": "stopped"})
    else:
        # Check if the processed files exist to determine success
        song_dir = file_management.get_song_dir(Path(filename))
        vocals_path = file_management.get_vocals_path_stem(song_dir).with_suffix(
            ".wav"
        )  # Or other extension
        instrumental_path = file_management.get_instrumental_path_stem(
            song_dir
        ).with_suffix(".wav")
        if vocals_path.exists() and instrumental_path.exists():
            return jsonify(
                {
                    "status": "success",
                    "vocals_path": str(vocals_path),
                    "instrumental_path": str(instrumental_path),
                }
            )
        else:
            return jsonify({"status": "not_found"})


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


if __name__ == "__main__":
    app.run(debug=True)
