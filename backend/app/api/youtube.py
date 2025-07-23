# backend/app/api/youtube.py
import logging

from app.api.responses import success_response
from app.exceptions import NetworkError, ServiceError, ValidationError
from app.schemas.requests import YouTubeDownloadRequest
from app.services.youtube_service import YouTubeService
from app.utils.error_handlers import handle_api_error
from app.utils.validation import validate_json_request
from flask import Blueprint, request

logger = logging.getLogger(__name__)
youtube_bp = Blueprint("youtube", __name__, url_prefix="/api/youtube")


@youtube_bp.route("/search", methods=["GET"])
@handle_api_error
def search_youtube_endpoint():
    """Search YouTube for videos - thin controller"""
    try:
        query = request.args.get("query")
        if not query:
            raise ValidationError("Missing query parameter", "MISSING_QUERY")

        max_results_str = request.args.get("maxResults", "10")
        try:
            max_results = int(max_results_str)
        except ValueError as e:
            raise ValidationError(
                "Invalid maxResults parameter, must be an integer",
                "INVALID_MAX_RESULTS",
            ) from e

        youtube_service = YouTubeService()
        results = youtube_service.search_videos(query, max_results)

        return success_response(
            data=results, message=f"Found {len(results)} videos matching '{query}'"
        )

    except ServiceError:
        raise  # Let error handlers deal with it
    except ConnectionError as e:
        raise NetworkError(
            "Failed to connect to YouTube API",
            "YOUTUBE_CONNECTION_ERROR",
            {"query": query, "error": str(e)},
        ) from e
    except TimeoutError as e:
        raise NetworkError(
            "YouTube API request timed out",
            "YOUTUBE_TIMEOUT_ERROR",
            {"query": query, "error": str(e)},
        ) from e
    except Exception as e:
        raise ServiceError(
            "Unexpected error during YouTube search",
            "YOUTUBE_SEARCH_ERROR",
            {"query": query, "error": str(e)},
        ) from e


@youtube_bp.route("/download", methods=["POST"])
@handle_api_error
@validate_json_request(YouTubeDownloadRequest)
def download_youtube_endpoint(validated_data: YouTubeDownloadRequest):
    """Download and process YouTube video - thin controller delegating to service"""

    # Delegate to service layer for job creation and orchestration
    # The service will handle song creation if needed
    youtube_service = YouTubeService()
    job_id = youtube_service.download_and_process_async(
        song_id=validated_data.song_id,
        video_id_or_url=validated_data.video_id,
        artist=validated_data.artist or "",
        title=validated_data.title or "",
    )

    logger.info(
        "YouTube processing started for song %s, video %s, job %s",
        validated_data.song_id,
        validated_data.video_id,
        job_id,
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
