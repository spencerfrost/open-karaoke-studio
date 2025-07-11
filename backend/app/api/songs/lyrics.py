from urllib.parse import unquote

from app.db.database import get_db_session
from app.exceptions import (
    NetworkError,
    ResourceNotFoundError,
    ServiceError,
    ValidationError,
)
from app.repositories.song_repository import SongRepository
from app.services.lyrics_service import LyricsService
from app.utils.error_handlers import handle_api_error
from flask import jsonify, request

from . import logger, song_bp


@song_bp.route("/<string:song_id>/lyrics", methods=["GET"])
@handle_api_error
def get_song_lyrics(song_id: str):
    """Fetch synchronized or plain lyrics for a song using LRCLIB."""
    logger.info("Received lyrics request for song %s", song_id)
    try:
        lyrics_service = LyricsService()
        stored_lyrics = lyrics_service.get_lyrics(song_id)
        if stored_lyrics:
            logger.info("Returning stored lyrics for song %s", song_id)
            return jsonify({"plainLyrics": stored_lyrics}), 200
        with get_db_session() as session:
            repo = SongRepository(session)
            db_song = repo.fetch(song_id)
        if not db_song:
            raise ResourceNotFoundError("Song", song_id)
        song_data = db_song.to_dict()
        title = song_data["title"]
        artist = (
            song_data["artist"]
            if song_data["artist"].lower() != "unknown artist"
            else song_data["channel"]
        )
        album = song_data["album"]
        if not title or not artist:
            raise ValidationError(
                "Missing essential info for lyrics lookup", "MISSING_METADATA"
            )
        query_parts = [artist, title]
        if album:
            query_parts.append(album)
        query = " ".join(query_parts)
        results = lyrics_service.search_lyrics(query)
        if results:
            lyrics_data = results[0]
            logger.info("Found lyrics for %s", song_id)
            if lyrics_data.get("plainLyrics"):
                try:
                    lyrics_service.save_lyrics(song_id, lyrics_data["plainLyrics"])
                except OSError as e:
                    logger.warning(
                        "Failed to save lyrics locally (file system error): %s", e
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to save lyrics locally (unexpected error): %s", e
                    )
            return jsonify(lyrics_data), 200
        else:
            logger.info("No lyrics found for %s", song_id)
            raise ResourceNotFoundError("Lyrics", song_id)
    except ServiceError:
        raise
    except ConnectionError as e:
        raise NetworkError(
            "Failed to connect to lyrics service",
            "LYRICS_CONNECTION_ERROR",
            {"song_id": song_id, "error": str(e)},
        )
    except TimeoutError as e:
        raise NetworkError(
            "Lyrics service request timed out",
            "LYRICS_TIMEOUT_ERROR",
            {"song_id": song_id, "error": str(e)},
        )
    except Exception as e:
        raise ServiceError(
            "Unexpected error fetching lyrics",
            "LYRICS_FETCH_ERROR",
            {"song_id": song_id, "error": str(e)},
        )
