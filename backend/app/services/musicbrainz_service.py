"""MusicBrainz recording search service."""

import json
import logging
import re
import time
from pathlib import Path

import httpx

from app.services.artist_parsing import ArtistCredit, clean_artist_name

logger = logging.getLogger(__name__)

_MB_BASE = "https://musicbrainz.org/ws/2"
_USER_AGENT = "OpenKaraokeStudio/1.0 (https://github.com/open-karaoke-studio)"
_TIMEOUT = 10.0
# Seconds before each try: the first keeps to 1 request/sec, the rest back off.
_RETRY_WAITS = (1, 4, 10)

_FEAT_JOINPHRASE = re.compile(r"\bfeat\.?\b|\bfeaturing\b|\bft\.?\b", re.IGNORECASE)

# Strips trailing/inline parenthetical boilerplate from soundtrack titles,
# e.g. "Wicked (Original Broadway Cast Recording)" -> "Wicked".
_BOILERPLATE_PAREN = re.compile(r"\s*\([^)]*\)")


def _is_placeholder(name: str) -> bool:
    """A MusicBrainz special-purpose artist: "[unknown]", "Various Artists"."""
    return (name.startswith("[") and name.endswith("]")) or (
        name.casefold() == "various artists"
    )


def _parse_artist_credits(artist_credit_list: list) -> list[ArtistCredit]:
    """Return the credits in a MusicBrainz artist-credit array.

    Role is determined by the joinphrase between artists:
    - Artists joined by '&', ',', 'and', 'with' etc. share the current role
    - After a joinphrase containing 'feat.'/'featuring'/'ft.', subsequent artists
      are marked 'featured'

    This correctly distinguishes "Amber Mark & John The Blind" (two primaries)
    from "Bob Marley & The Wailers" (single MB artist entity).

    Each credit keeps the artist's MusicBrainz id and current name, and the
    name as this recording prints it ("Dixie Chicks" for The Chicks).

    MusicBrainz's placeholder artists ("[theatre]", "[unknown]", "Various
    Artists") aren't artists: such a credit is filed under the name it
    prints, without the id, and dropped when that's the placeholder too.
    """
    if not artist_credit_list:
        return []

    result: list[ArtistCredit] = []
    current_role = "primary"

    for ac in artist_credit_list:
        artist = ac.get("artist") or {}
        credited = clean_artist_name(ac.get("name") or artist.get("name") or "")
        name = clean_artist_name(artist.get("name") or credited)
        mbid = artist.get("id")
        if _is_placeholder(name):
            name, mbid = credited, None
        if name and not _is_placeholder(name):
            result.append(
                ArtistCredit(
                    name=name,
                    role=current_role,
                    musicbrainz_id=mbid,
                    credited_as=credited or name,
                )
            )

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

        # Names as the recording prints them
        primary_artists = [
            c.credited_as or c.name for c in artist_credits if c.role == "primary"
        ]
        featured_artists = [
            c.credited_as or c.name for c in artist_credits if c.role == "featured"
        ]
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
                "artistCredits": [
                    {
                        "name": c.credited_as or c.name,
                        "role": c.role,
                        "musicbrainzId": c.musicbrainz_id,
                    }
                    for c in artist_credits
                ],
                "album": release.get("title", ""),
                "releaseDate": release.get("date", ""),
                "duration": r.get("length"),  # milliseconds, may be None
            }
        )

    return results


def _strip_show_name_boilerplate(title: str) -> str:
    """Remove parenthetical boilerplate from a soundtrack/show title."""
    return _BOILERPLATE_PAREN.sub("", title).strip()


def _extract_show_name(data: dict) -> str | None:
    """Pull a show/soundtrack name out of a recording's releases, if any.

    If any release-group carries a "Soundtrack" secondary type, returns its
    title with boilerplate parentheticals stripped (e.g. "Wicked").
    """
    for release in data.get("releases", []):
        rg = release.get("release-group") or {}
        secondary_types = rg.get("secondary-types") or []
        if "Soundtrack" in secondary_types:
            title = rg.get("title") or release.get("title") or ""
            show_name = _strip_show_name_boilerplate(title)
            if show_name:
                return show_name

    return None


def _fetch(path: str, params: dict, cache_dir: Path | None) -> dict | None:
    """GET a MusicBrainz resource, or None if the lookup fails.

    With `cache_dir`, a response saved there by an earlier call is used
    instead, and a new one is saved. Failures aren't cached. Rate-limited to
    ~1 request/sec to respect MusicBrainz guidelines; a cached answer doesn't
    wait.
    """
    cache_file = cache_dir / f"{path.replace('/', '-')}.json" if cache_dir else None
    if cache_file and cache_file.exists():
        try:
            return json.loads(cache_file.read_text())
        except (OSError, ValueError):
            logger.warning("Unreadable MusicBrainz cache file %s", cache_file)

    headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
    # A 503 is MusicBrainz's rate limit: wait longer and ask again.
    for attempt, wait in enumerate(_RETRY_WAITS):
        time.sleep(wait)
        try:
            with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = client.get(
                    f"{_MB_BASE}/{path}",
                    params={**params, "fmt": "json"},
                    headers=headers,
                )
                resp.raise_for_status()
            data = resp.json()
            break
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503 and attempt < len(_RETRY_WAITS) - 1:
                continue
            logger.warning("MusicBrainz lookup failed for %s: %s", path, e)
            return None
        except (httpx.HTTPError, ValueError) as e:
            logger.warning("MusicBrainz lookup failed for %s: %s", path, e)
            return None

    if cache_file:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(data))
    return data


def get_recording_details(
    recording_id: str, cache_dir: Path | None = None
) -> tuple[str | None, list[ArtistCredit] | None]:
    """Return (show_name, artist_credits) for a recording in a single request.

    Both values come off the same /recording resource, so they are fetched
    together — asking twice would double both the round trips and the
    rate-limit sleep for no benefit. Either element is None when absent
    from the response; both are None if the lookup fails.
    """
    data = _fetch(
        f"recording/{recording_id}",
        {"inc": "releases release-groups artist-credits"},
        cache_dir,
    )
    if data is None:
        return None, None

    raw_credits = data.get("artist-credit", [])
    # A recording credited only to placeholders has no credits to use.
    credits = _parse_artist_credits(raw_credits) or None

    return _extract_show_name(data), credits


def get_artist_aliases(
    artist_id: str, cache_dir: Path | None = None
) -> list[str] | None:
    """An artist's current name, then the other names MusicBrainz lists for them.

    None if the lookup fails.
    """
    data = _fetch(f"artist/{artist_id}", {"inc": "aliases"}, cache_dir)
    return artist_aliases_from(data) if data is not None else None


def artist_aliases_from(data: dict) -> list[str]:
    """The names in an /artist response: its own name and its aliases."""
    names = [data.get("name") or ""]
    names += [a.get("name") or "" for a in data.get("aliases") or []]
    return [clean_artist_name(n) for n in names if n and n.strip()]
