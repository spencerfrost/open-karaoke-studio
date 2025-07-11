"""Songs API Artists Module"""

from app.db.database import get_db_session
from app.db.models.song import DbSong
from app.exceptions import DatabaseError, ValidationError
from app.repositories.song_repository import SongRepository
from app.schemas.song import Song
from app.utils.error_handlers import handle_api_error
from flask import jsonify, request

from . import logger, song_bp


@song_bp.route("/artists", methods=["GET"])
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
        with get_db_session() as session:
            repo = SongRepository(session)
            from sqlalchemy import func

            artists_query = session.query(
                DbSong.artist,
                func.count(DbSong.id).label(
                    "song_count"
                ),  # pylint: disable=not-callable
            )
            if search_term:
                artists_query = artists_query.filter(
                    DbSong.artist.ilike(f"%{search_term}%")
                )
            artists_query = artists_query.group_by(DbSong.artist).order_by(
                DbSong.artist
            )
            artists = artists_query.offset(offset).limit(limit).all()
            artists = [
                {
                    "name": artist,
                    "songCount": song_count,
                    "firstLetter": artist[0].upper() if artist else "?",
                }
                for artist, song_count in artists
            ]

        total_count = 0
        with get_db_session() as session:
            repo = SongRepository(session)
            from sqlalchemy import func

            total_query = session.query(DbSong.artist).distinct()
            if search_term:
                total_query = total_query.filter(
                    DbSong.artist.ilike(f"%{search_term}%")
                )
            total_count = total_query.count()

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
        raise ValidationError(
            f"Invalid query parameters: {str(e)}", "INVALID_PARAMETERS"
        )
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


@song_bp.route("/by-artist/<string:artist_name>", methods=["GET"])
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
        with get_db_session() as session:
            repo = SongRepository(session)
            base_query = session.query(DbSong).filter(DbSong.artist == artist_name)
            sort_field = getattr(DbSong, sort_by, DbSong.title)
            if direction.lower() == "desc":
                base_query = base_query.order_by(sort_field.desc())
            else:
                base_query = base_query.order_by(sort_field.asc())
            total_count = base_query.count()
            songs = base_query.offset(offset).limit(limit).all()
            songs_data = {"songs": songs, "total": total_count}

            # Convert DbSong objects to Pydantic Song models for API response
            songs = [
                Song.model_validate(song.to_dict()).model_dump()
                for song in songs_data["songs"]
            ]
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
        raise ValidationError(
            f"Invalid query parameters: {str(e)}", "INVALID_PARAMETERS"
        )
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
