# backend/app/api/songs_artists.py

import logging
from flask import Blueprint, current_app, jsonify, request

from ..db.song_operations import (
    get_artists_total_count,
    get_artists_with_counts,
    get_songs_by_artist,
    search_songs_paginated,
)
from ..schemas.song import Song
from ..exceptions import DatabaseError, ValidationError
from ..utils.error_handlers import handle_api_error

logger = logging.getLogger(__name__)
artists_bp = Blueprint("songs_artists", __name__, url_prefix="/api/songs")


@artists_bp.route("/artists", methods=["GET"])
@handle_api_error
def get_artists():
    """Get all unique artists with song counts and optional filtering.

    Query Parameters:
        search: Optional search term to filter artists
        limit: Maximum number of artists to return (default: 100)
        offset: Number of artists to skip (default: 0)
    """
    try:
        search_term = request.args.get("search", "").strip()
        limit = min(int(request.args.get("limit", 100)), 200)  # Cap at 200
        offset = int(request.args.get("offset", 0))

        # Get artists with song counts from database
        artists = get_artists_with_counts(search_term=search_term, limit=limit, offset=offset)

        total_count = get_artists_total_count(search_term=search_term)

        response = {
            "artists": artists,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "hasMore": offset + limit < total_count,
            },
        }

        logger.info("Returning %s artists (total: %s)", len(artists), total_count)
        return jsonify(response)

    except ValueError as e:
        raise ValidationError(f"Invalid query parameters: {str(e)}", "INVALID_PARAMETERS")
    except ConnectionError as e:
        raise DatabaseError(
            "Database connection failed while fetching artists",
            "DATABASE_CONNECTION_ERROR",
            {"error": str(e)},
        )
    except Exception as e:
        raise DatabaseError(
            "Unexpected error fetching artists",
            "ARTISTS_FETCH_ERROR",
            {"error": str(e)},
        )


@artists_bp.route("/by-artist/<string:artist_name>", methods=["GET"])
@handle_api_error
def get_songs_by_artist_route(artist_name: str):
    """Get songs for a specific artist with pagination.

    Query Parameters:
        limit: Maximum number of songs to return (default: 20)
        offset: Number of songs to skip (default: 0)
        sort: Sort order - 'title', 'album', 'year', 'dateAdded' (default: 'title')
        direction: 'asc' or 'desc' (default: 'asc')
    """
    try:
        limit = min(int(request.args.get("limit", 20)), 100)  # Cap at 100 per page
        offset = int(request.args.get("offset", 0))
        sort_by = request.args.get("sort", "title")
        direction = request.args.get("direction", "asc")

        # Validate sort parameters
        valid_sorts = ["title", "album", "year", "dateAdded"]
        if sort_by not in valid_sorts:
            raise ValidationError(
                f"Invalid sort field: {sort_by}. Must be one of: {', '.join(valid_sorts)}",
                "INVALID_SORT_FIELD",
            )

        if direction not in ["asc", "desc"]:
            raise ValidationError(
                f"Invalid sort direction: {direction}. Must be 'asc' or 'desc'",
                "INVALID_SORT_DIRECTION",
            )

        # Get songs for artist from database
        songs_data = get_songs_by_artist(
            artist_name=artist_name,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            direction=direction,
        )

        # Convert DbSong objects to Pydantic Song models for API response
        songs = [Song.model_validate(song.to_dict()).model_dump() for song in songs_data["songs"]]
        total_count = songs_data["total"]

        response = {
            "songs": songs,
            "artist": artist_name,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "hasMore": offset + limit < total_count,
            },
        }

        logger.info(
            "Returning %s songs for artist '%s' (total: %s)",
            len(songs),
            artist_name,
            total_count,
        )
        return jsonify(response)

    except ValidationError:
        raise  # Let error handlers deal with it
    except ValueError as e:
        raise ValidationError(f"Invalid query parameters: {str(e)}", "INVALID_PARAMETERS")
    except ConnectionError as e:
        raise DatabaseError(
            f"Database connection failed while fetching songs for artist '{artist_name}'",
            "DATABASE_CONNECTION_ERROR",
            {"artist": artist_name, "error": str(e)},
        )
    except Exception as e:
        raise DatabaseError(
            f"Unexpected error fetching songs for artist '{artist_name}'",
            "ARTIST_SONGS_FETCH_ERROR",
            {"artist": artist_name, "error": str(e)},
        )


@artists_bp.route("/search", methods=["GET"])
@handle_api_error
def search_songs():
    """Enhanced search with pagination and artist grouping options.

    Query Parameters:
        q: Search query (required)
        limit: Maximum number of songs to return (default: 20)
        offset: Number of songs to skip (default: 0)
        group_by_artist: If true, group results by artist (default: false)
        sort: Sort order (default: 'relevance')
        direction: 'asc' or 'desc' (default: 'desc')
    """
    try:
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify(
                {
                    "songs": [],
                    "pagination": {
                        "total": 0,
                        "limit": 0,
                        "offset": 0,
                        "hasMore": False,
                    },
                }
            )

        limit = min(int(request.args.get("limit", 20)), 100)
        offset = int(request.args.get("offset", 0))
        group_by_artist = request.args.get("group_by_artist", "false").lower() == "true"
        sort_by = request.args.get("sort", "relevance")
        direction = request.args.get("direction", "desc")

        # Validate parameters
        if direction not in ["asc", "desc"]:
            raise ValidationError(
                f"Invalid sort direction: {direction}. Must be 'asc' or 'desc'",
                "INVALID_SORT_DIRECTION",
            )

        # Get search results from database
        search_results = search_songs_paginated(
            query=query,
            limit=limit,
            offset=offset,
            group_by_artist=group_by_artist,
            sort_by=sort_by,
            direction=direction,
        )

        if group_by_artist:
            # Group results by artist
            response = {
                "artists": search_results["artists"],  # [{artist: "...", songs: [...], count: N}]
                "totalSongs": search_results["total_songs"],
                "totalArtists": search_results["total_artists"],
                "pagination": search_results["pagination"],
            }
        else:
            # Flat list of songs - convert using new pattern
            songs = [
                Song.model_validate(song.to_dict()).model_dump() for song in search_results["songs"]
            ]
            response = {"songs": songs, "pagination": search_results["pagination"]}

        logger.info(
            "Search '%s' returned %s results",
            query,
            search_results["pagination"]["total"],
        )
        return jsonify(response)

    except ValidationError:
        raise  # Let error handlers deal with it
    except ValueError as e:
        raise ValidationError(f"Invalid query parameters: {str(e)}", "INVALID_PARAMETERS")
    except ConnectionError as e:
        raise DatabaseError(
            "Database connection failed during song search",
            "DATABASE_CONNECTION_ERROR",
            {"query": query, "error": str(e)},
        )
    except Exception as e:
        raise DatabaseError(
            "Unexpected error searching songs",
            "SONGS_SEARCH_ERROR",
            {"query": query, "error": str(e)},
        )
