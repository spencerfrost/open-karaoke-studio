"""Resolve structured artist credits for a song via MB recording → MB search → regex fallback."""

import logging

from app.services.artist_parsing import normalize_artist_name, parse_song_artists

logger = logging.getLogger(__name__)

_MIN_SEARCH_SCORE = 0.90


def _credits_include_artist(credits: list[tuple[str, str]], expected: str) -> bool:
    """True if `expected` names one of the credited artists, or all the primaries together.

    The joined form covers a song saved as "Amber Mark & John The Blind" that
    MusicBrainz credits as two separate primary artists.
    """
    expected_key = normalize_artist_name(expected)
    if not expected_key:
        return False
    candidates = [name for name, _ in credits]
    candidates.append(" & ".join(name for name, role in credits if role == "primary"))
    return any(normalize_artist_name(name) == expected_key for name in candidates)


def resolve_artist_credits(
    title: str,
    artist_str: str,
    recording_credits: list[tuple[str, str]] | None = None,
) -> list[tuple[str, str]]:
    """Return [(name, role), ...] using the best available source.

    Resolution order:
    1. Credits already fetched from the song's MusicBrainz recording
    2. MusicBrainz search by title + artist (score >= 0.90 and the credits
       include the song's primary artist)
    3. Regex parsing of the raw artist_str

    The caller passes step 1's credits in rather than having this fetch them,
    because the same recording lookup also yields the show name — doing it here
    would mean requesting the same resource twice.

    Step 2 checks the artist because a search hit can be a different artist's
    recording whose title happens to match — e.g. a cover uploaded as
    "Norah Jones - Don't Know Why" by someone else.
    """
    from app.services import musicbrainz_service

    # 1. Credits from the recording lookup the caller already performed
    if recording_credits:
        logger.info("Resolved credits via MB recording")
        return recording_credits

    # 2. Search MusicBrainz
    primary_from_regex, _ = parse_song_artists(artist_str)
    try:
        query = f'recording:"{title}" artistname:"{primary_from_regex}"'
        results = musicbrainz_service.search_recordings(query, limit=5)
        # Results are sorted by score, so stop at the first one below the bar.
        for result in results:
            if result["score"] < _MIN_SEARCH_SCORE:
                break
            if not _credits_include_artist(result["artistCredits"], primary_from_regex):
                logger.info(
                    "Rejected MB search result for '%s' / '%s': credited to %s, "
                    "not '%s' (score=%.2f, recording=%s)",
                    title,
                    artist_str,
                    [name for name, _ in result["artistCredits"]],
                    primary_from_regex,
                    result["score"],
                    result.get("recordingId"),
                )
                continue
            logger.info("Resolved credits via MB search (score=%.2f)", result["score"])
            return result["artistCredits"]
    except Exception:
        logger.warning(
            "MB search failed for '%s' / '%s'", title, artist_str, exc_info=True
        )

    # 3. Fallback: regex
    primary, featured = parse_song_artists(artist_str)
    credits: list[tuple[str, str]] = [(primary, "primary")]
    credits.extend((name, "featured") for name in featured)
    return credits
