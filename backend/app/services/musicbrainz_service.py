"""MusicBrainz recording search service."""

import logging

import httpx

logger = logging.getLogger(__name__)

_MB_BASE = "https://musicbrainz.org/ws/2"
_USER_AGENT = "OpenKaraokeStudio/1.0 (https://github.com/open-karaoke-studio)"
_TIMEOUT = 10.0


def search_recordings(query: str, limit: int = 10) -> list[dict]:
    """
    Search MusicBrainz recordings by free-text query.

    Returns a list of candidates sorted by MusicBrainz score descending:
      {score, recordingId, title, artist, album, duration, releaseDate}
    """
    params = {"query": query, "fmt": "json", "limit": limit}
    headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(f"{_MB_BASE}/recording/", params=params, headers=headers)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("MusicBrainz search failed: %s", e)
        raise

    recordings = resp.json().get("recordings", [])
    results = []
    for r in recordings:
        artist_credits = r.get("artist-credit", [])
        artist = (
            artist_credits[0].get("name") or artist_credits[0].get("artist", {}).get("name", "")
            if artist_credits
            else ""
        )

        releases = r.get("releases", [])
        release = releases[0] if releases else {}

        results.append(
            {
                "score": r.get("score", 0) / 100.0,  # normalise to 0-1
                "recordingId": r["id"],
                "title": r.get("title", ""),
                "artist": artist,
                "album": release.get("title", ""),
                "releaseDate": release.get("date", ""),
                "duration": r.get("length"),  # milliseconds, may be None
            }
        )

    return results
