"""Resolve structured artist credits for a song via MB recording → MB search → regex fallback."""

import logging

from app.services.artist_parsing import parse_song_artists

logger = logging.getLogger(__name__)


def resolve_artist_credits(
    title: str,
    artist_str: str,
    recording_id: str | None = None,
) -> list[tuple[str, str]]:
    """Return [(name, role), ...] using the best available source.

    Resolution order:
    1. MusicBrainz recording lookup (if recording_id is set)
    2. MusicBrainz search by title + artist (if score >= 0.90)
    3. Regex parsing of the raw artist_str
    """
    from app.services import musicbrainz_service

    # 1. Direct recording lookup
    if recording_id:
        try:
            result = musicbrainz_service.get_recording_credits(recording_id)
            if result:
                logger.info("Resolved credits via MB recording %s", recording_id)
                return result
        except Exception:
            logger.warning(
                "MB recording lookup failed for %s", recording_id, exc_info=True
            )

    # 2. Search MusicBrainz
    primary_from_regex, _ = parse_song_artists(artist_str)
    try:
        query = f'recording:"{title}" artistname:"{primary_from_regex}"'
        results = musicbrainz_service.search_recordings(query, limit=5)
        if results and results[0]["score"] >= 0.90:
            best = results[0]
            logger.info(
                "Resolved credits via MB search (score=%.2f)", best["score"]
            )
            return best["artistCredits"]
    except Exception:
        logger.warning("MB search failed for '%s' / '%s'", title, artist_str, exc_info=True)

    # 3. Fallback: regex
    primary, featured = parse_song_artists(artist_str)
    credits: list[tuple[str, str]] = [(primary, "primary")]
    credits.extend((name, "featured") for name in featured)
    return credits
