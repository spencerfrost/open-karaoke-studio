# backend/app/api/youtube.py
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone

from ..services.youtube_service import (
    search_youtube,
    download_from_youtube,
)
from ..services.file_management import get_song_dir
from ..tasks.tasks import process_audio_task, job_store
from ..db.models import Job, JobStatus

youtube_bp = Blueprint("youtube", __name__, url_prefix="/api/youtube")


@youtube_bp.route("/search", methods=["GET"])
def search_youtube_endpoint():
    """Endpoint to search YouTube for videos."""
    try:
        query = request.args.get("query")
        if not query:
            return jsonify({"error": "Missing query parameter"}), 400
            
        max_results_str = request.args.get("maxResults", "10")
        try:
            max_results = int(max_results_str)
        except ValueError:
            return jsonify({"error": "Invalid maxResults parameter, must be an integer"}), 400


        current_app.logger.info(f"Searching YouTube for: {query}")
        results = search_youtube(query, max_results) 
        return jsonify({"data": results})
    except Exception as e:
        current_app.logger.error(f"YouTube search error: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error during YouTube search: {str(e)}"}), 500


@youtube_bp.route("/download", methods=["POST"])
def download_youtube_endpoint():
    """
    Endpoint to download a YouTube video and queue it for processing.
    This endpoint immediately returns and performs the download in the background.
    """
    try:
        data = request.get_json()
        if not data or "videoId" not in data:
            return jsonify({"error": "Missing videoId parameter"}), 400
            
        artist = data.get("artist", "")
        song_title = data.get("title", "")
        album = data.get("album", "")
        
        # Get a reference to the current app for use in the background thread
        app = current_app._get_current_object()  # Get the actual app instance, not the proxy
        
        # Start a background thread to download and process without making the request wait
        def background_download():
            # Create an application context for this thread
            with app.app_context():
                try:
                    # Download YouTube video
                    song_id, metadata = download_from_youtube(data["videoId"], artist, song_title)
                    
                    # Queue audio processing
                    song_dir = get_song_dir(song_id)
                    original_file_path = song_dir / "original.mp3"
                    
                    if original_file_path.exists():
                        app.logger.info(f"Submitting audio processing task for song {song_id}")
                        try:
                            job = Job(
                                id=song_id,
                                filename=original_file_path.name,
                                status=JobStatus.PENDING,
                                created_at=datetime.now(timezone.utc),
                            )
                            job_store.save_job(job)
                            
                            task = process_audio_task.delay(song_id)
                            
                            job.task_id = task.id
                            job.status = JobStatus.PROCESSING
                            job_store.save_job(job)
                        except Exception as task_error:
                            app.logger.error(f"Failed to submit processing task: {task_error}", exc_info=True)
                    else:
                        app.logger.error(f"Original audio file not found at {original_file_path}")
                except Exception as e:
                    app.logger.error(f"Background download error: {str(e)}", exc_info=True)
        
        import threading
        download_thread = threading.Thread(target=background_download)
        download_thread.daemon = True
        download_thread.start()
        
        temp_id = data["videoId"]
        return jsonify({
            "tempId": temp_id,
            "status": "downloading",
            "message": "Download and processing started in background"
        }), 202  # 202 Accepted indicates the request is being processed asynchronously
    except Exception as e:
        current_app.logger.error(f"YouTube download error: {str(e)}", exc_info=True)
        return jsonify({"error": f"Failed to download from YouTube: {str(e)}"}), 500
