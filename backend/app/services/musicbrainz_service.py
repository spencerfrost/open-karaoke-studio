"""MusicBrainz recording search service."""

import logging
import re
import time

import httpx

logger = logging.getLogger(__name__)

_MB_BASE = "https://musicbrainz.org/ws/2"
_USER_AGENT = "OpenKaraokeStudio/1.0 (https://github.com/open-karaoke-studio)"
_TIMEOUT = 10.0

_FEAT_JOINPHRASE = re.compile(r"\bfeat\.?\b|\bfeaturing\b|\bft\.?\b", re.IGNORECASE)


def _parse_artist_credits(
    artist_credit_list: list,
) -> list[tuple[str, str]]:
    """Return [(name, role), ...] from a MusicBrainz artist-credit array.

    Role is determined by the joinphrase between artists:
    - Artists joined by '&', ',', 'and', 'with' etc. share the current role
    - After a joinphrase containing 'feat.'/'featuring'/'ft.', subsequent artists
      are marked 'featured'

    This correctly distinguishes "Amber Mark & John The Blind" (two primaries)
    from "Bob Marley & The Wailers" (single MB artist entity).
    """
    if not artist_credit_list:
        return []

    result: list[tuple[str, str]] = []
    current_role = "primary"

    for ac in artist_credit_list:
        name = ac.get("name") or ac.get("artist", {}).get("name", "")
        if not name:
            continue
        result.append((name, current_role))

        # Check if joinphrase signals a switch to featured
        joinphrase = ac.get("joinphrase", "")
        if _FEAT_JOINPHRASE.search(joinphrase):
            current_role = "featured"

    return result


def search_recordings(query: str, limit: int = 10) -> list[dict]:
    """
    Search MusicBrainz recordings by free-text query.

    Returns a list of candidates sorted by MusicBrainz score descending:
      {score, recordingId, title, artist, primaryArtist, featuredArtists, album, duration, releaseDate}
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
        raw_credits = r.get("artist-credit", [])
        artist_credits = _parse_artist_credits(raw_credits)

        # Derive legacy primary/featured fields for backward compat
        primary_artists = [n for n, role in artist_credits if role == "primary"]
        featured_artists = [n for n, role in artist_credits if role == "featured"]
        primary_artist = primary_artists[0] if primary_artists else ""

        # Combined display string
        artist = " & ".join(primary_artists)
        if featured_artists:
            artist = f"{artist} feat. {', '.join(featured_artists)}"

        releases = r.get("releases", [])
        release = releases[0] if releases else {}

        results.append(
            {
                "score": r.get("score", 0) / 100.0,  # normalise to 0-1
                "recordingId": r["id"],
                "title": r.get("title", ""),
                "artist": artist,
                "primaryArtist": primary_artist,
                "featuredArtists": featured_artists,
                "artistCredits": artist_credits,
                "album": release.get("title", ""),
                "releaseDate": release.get("date", ""),
                "duration": r.get("length"),  # milliseconds, may be None
            }
        )

    return results


def get_recording_credits(recording_id: str) -> list[tuple[str, str]] | None:
    """Fetch artist credits for a specific MusicBrainz recording.

    Returns [(name, role), ...] or None on failure.
    Rate-limited to ~1 request/sec to respect MusicBrainz guidelines.
    """
    time.sleep(1)

    headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
    params = {"inc": "artist-credits", "fmt": "json"}

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(
                f"{_MB_BASE}/recording/{recording_id}",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("MusicBrainz recording lookup failed for %s: %s", recording_id, e)
        return None

    data = resp.json()
    credits = data.get("artist-credit", [])
    if not credits:
        return None

    return _parse_artist_credits(credits)
