# backend/app/api/metadata.py

import logging

from app.exceptions import NetworkError, ServiceError, ValidationError
from app.services.metadata_service import MetadataService
from app.utils.error_handlers import handle_api_error
from flask import Blueprint, current_app, jsonify, request

logger = logging.getLogger(__name__)
# Create a metadata blueprint with the new, clean URL structure
metadata_bp = Blueprint("metadata", __name__, url_prefix="/api/metadata")


@metadata_bp.route("/search", methods=["GET"])
@handle_api_error
def search_metadata_endpoint():
    """Endpoint to search for song metadata using iTunes Search API."""
    logger.info("Received metadata search request")

    try:
        # Get search terms from query parameters
        title = request.args.get("title", "").strip()
        artist = request.args.get("artist", "").strip()
        album = request.args.get("album", "").strip()
        limit = int(request.args.get("limit", 5))
        sort_by = request.args.get(
            "sort_by", "relevance"
        )  # For backwards compatibility

        # Validate that at least title or artist is provided
        if not title and not artist:
            raise ValidationError(
                "At least one of 'title' or 'artist' parameters is required",
                "MISSING_SEARCH_PARAMETERS",
            )

        # Validate limit
        if limit <= 0 or limit > 50:
            raise ValidationError("Limit must be between 1 and 50", "INVALID_LIMIT")

        logger.info(
            "Metadata search - Artist: '%s', Title: '%s', Album: '%s', Limit: %s",
            artist,
            title,
            album,
            limit,
        )

        # Initialize service
        metadata_service = MetadataService()

        # Search using the service layer
        results = metadata_service.search_metadata(artist, title, album, limit)

        # Format response using service
        search_params = {
            "artist": artist,
            "title": title,
            "album": album,
            "limit": limit,
            "sort_by": sort_by,
        }
        response_data = metadata_service.format_metadata_response(
            results, search_params
        )

        logger.info("Metadata search returned %s results", len(results))
        return jsonify(response_data), 200

    except ValueError as e:
        raise ValidationError(f"Invalid parameter: {str(e)}", "INVALID_PARAMETERS")
    except ValidationError:
        raise  # Let error handlers deal with it
    except ConnectionError as e:
        raise NetworkError(
            "Failed to connect to metadata service",
            "METADATA_CONNECTION_ERROR",
            {"error": str(e)},
        )
    except TimeoutError as e:
        raise NetworkError(
            "Metadata service request timed out",
            "METADATA_TIMEOUT_ERROR",
            {"error": str(e)},
        )
    except Exception as e:
        raise ServiceError(
            "Unexpected error during metadata search",
            "METADATA_SEARCH_ERROR",
            {"error": str(e)},
        )
