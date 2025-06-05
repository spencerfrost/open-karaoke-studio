# backend/app/api/youtube.py
from flask import Blueprint, request, current_app

from ..services.youtube_service import YouTubeService
from ..services.song_service import SongService
from ..api.responses import success_response, error_response
from ..exceptions import ServiceError, ValidationError

youtube_bp = Blueprint("youtube", __name__, url_prefix="/api/youtube")


@youtube_bp.route("/search", methods=["GET"])
def search_youtube_endpoint():
    """Search YouTube for videos - thin controller"""
    try:
        query = request.args.get("query")
        if not query:
            return error_response("Missing query parameter", 400)
            
        max_results_str = request.args.get("maxResults", "10")
        try:
            max_results = int(max_results_str)
        except ValueError:
            return error_response("Invalid maxResults parameter, must be an integer", 400)

        youtube_service = YouTubeService()
        results = youtube_service.search_videos(query, max_results)
        
        return success_response(
            data=results,
            message=f"Found {len(results)} videos matching '{query}'"
        )
        
    except ServiceError as e:
        return error_response(str(e), 500)
    except Exception as e:
        current_app.logger.error(f"Unexpected error in YouTube search: {e}")
        return error_response("Internal server error", 500)


@youtube_bp.route("/download", methods=["POST"])
def download_youtube_endpoint():
    """Download and process YouTube video - thin controller"""
    try:
        data = request.get_json()
        if not data or "videoId" not in data:
            return error_response("Missing videoId parameter", 400)
            
        artist = data.get("artist", "")
        song_title = data.get("title", "")
        existing_song_id = data.get("songId")
        
        # Create YouTube service with Song service dependency
        song_service = SongService()
        youtube_service = YouTubeService(song_service=song_service)
        
        # Start async download and processing
        song_id = youtube_service.download_and_process_async(
            video_id_or_url=data["videoId"],
            artist=artist,
            title=song_title,
            song_id=existing_song_id
        )
        
        return success_response(
            data={
                "songId": song_id,
                "status": "processing",
                "message": "Download and processing started"
            },
            message="YouTube video download started",
            status_code=202
        )
        
    except ValidationError as e:
        return error_response(str(e), 400)
    except ServiceError as e:
        return error_response(str(e), 500)
    except Exception as e:
        current_app.logger.error(f"Unexpected error in YouTube download: {e}")
        return error_response("Internal server error", 500)
