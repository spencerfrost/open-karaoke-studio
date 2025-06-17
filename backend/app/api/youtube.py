# backend/app/api/youtube.py
from flask import Blueprint, current_app, request

from ..api.responses import error_response, success_response
from ..exceptions import ServiceError, ValidationError
from ..services.youtube_service import YouTubeService

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
            data=results, message=f"Found {len(results)} videos matching '{query}'"
        )

    except ServiceError as e:
        return error_response(str(e), 500)
    except Exception as e:
        current_app.logger.error("Unexpected error in YouTube search: %s", e)
        return error_response("Internal server error", 500)


@youtube_bp.route("/download", methods=["POST"])
def download_youtube_endpoint():
    """Download and process YouTube video - thin controller delegating to service"""
    try:
        data = request.get_json()
        if not data or "videoId" not in data:
            return error_response("Missing videoId parameter", 400)

        video_id = data["videoId"]
        artist = data.get("artist", "")
        song_title = data.get("title", "")
        song_id = data.get("songId")

        # Validate required parameters
        if not song_id:
            return error_response("Missing songId parameter", 400)

        # Delegate to service layer for job creation and orchestration
        # The service will handle song creation if needed
        youtube_service = YouTubeService()
        job_id = youtube_service.download_and_process_async(
            video_id_or_url=video_id, artist=artist, title=song_title, song_id=song_id
        )

        current_app.logger.info(
            "YouTube processing started for song %s, video %s, job %s", song_id, video_id, job_id
        )

        return success_response(
            data={
                "jobId": job_id,
                "status": "pending",
                "message": "YouTube processing job created",
            },
            message="YouTube processing started",
            status_code=202,
        )

    except ValidationError as e:
        return error_response(str(e), 400)
    except ServiceError as e:
        return error_response(str(e), 500)
    except Exception as e:
        current_app.logger.error("Unexpected error in YouTube download: %s", e)
        return error_response("Internal server error", 500)
