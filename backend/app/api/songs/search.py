"""Songs API Search Module"""

from app.db.database import get_db_session
from app.db.models.song import DbSong
from app.exceptions import DatabaseError, ValidationError
from app.schemas.song import Song
from app.utils.error_handlers import handle_api_error
from flask import jsonify, request
from sqlalchemy import func, or_

from . import logger, song_bp


@song_bp.route("/search", methods=["GET"])
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
        with get_db_session() as session:
            search_filter = or_(
                DbSong.title.ilike(f"%{query}%"),
                DbSong.artist.ilike(f"%{query}%"),
                DbSong.album.ilike(f"%{query}%"),
            )
            if group_by_artist:
                artist_query = (
                    session.query(
                        DbSong.artist,
                        func.count(DbSong.id).label(
                            "song_count"
                        ),  # pylint: disable=not-callable
                    )
                    .filter(search_filter)
                    .group_by(DbSong.artist)
                )
                total_artists = artist_query.count()
                artist_results = artist_query.offset(offset).limit(limit).all()
                artists_data = []
                total_songs = 0
                for artist, count in artist_results:
                    songs_query = (
                        session.query(DbSong).filter(DbSong.artist == artist).limit(5)
                    )
                    songs = songs_query.all()
                    total_songs += count
                    artists_data.append(
                        {
                            "artist": artist,
                            "songCount": count,
                            "songs": songs,
                        }
                    )
                search_results = {
                    "artists": artists_data,
                    "total_songs": total_songs,
                    "total_artists": total_artists,
                    "pagination": {
                        "total": total_artists,
                        "limit": limit,
                        "offset": offset,
                        "hasMore": offset + limit < total_artists,
                    },
                }
            else:
                base_query = session.query(DbSong).filter(search_filter)
                if sort_by == "relevance":
                    base_query = base_query.order_by(
                        DbSong.title,
                        DbSong.artist,
                        DbSong.date_added.desc(),
                    )
                else:
                    sort_field = getattr(DbSong, sort_by, DbSong.title)
                    if direction.lower() == "desc":
                        base_query = base_query.order_by(sort_field.desc())
                    else:
                        base_query = base_query.order_by(sort_field.asc())
                total_count = base_query.count()
                songs = base_query.offset(offset).limit(limit).all()
                search_results = {
                    "songs": songs,
                    "pagination": {
                        "total": total_count,
                        "limit": limit,
                        "offset": offset,
                        "hasMore": offset + limit < total_count,
                    },
                }

        if group_by_artist:
            # Group results by artist
            response = {
                "artists": search_results[
                    "artists"
                ],  # [{artist: "...", songs: [...], count: N}]
                "totalSongs": search_results["total_songs"],
                "totalArtists": search_results["total_artists"],
                "pagination": search_results["pagination"],
            }
        else:
            # Flat list of songs - convert using new pattern
            songs = [
                Song.model_validate(song.to_dict()).model_dump()
                for song in search_results["songs"]
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
        raise ValidationError(
            f"Invalid query parameters: {str(e)}", "INVALID_PARAMETERS"
        ) from e
    except ConnectionError as e:
        raise DatabaseError(
            "Database connection failed during song search",
            "DATABASE_CONNECTION_ERROR",
            {"query": query, "error": str(e)},
        ) from e
    except Exception as e:
        raise DatabaseError(
            "Unexpected error searching songs",
            "SONGS_SEARCH_ERROR",
            {"query": query, "error": str(e)},
        ) from e
