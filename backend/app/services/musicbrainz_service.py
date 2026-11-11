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

_VARIOUS_ARTISTS_ID = "89ad4ac3-39f7-470e-963a-56509c546377"

_FEAT_JOINPHRASE = re.compile(r"\bfeat\.?\b|\bfeaturing\b|\bft\.?\b", re.IGNORECASE)

# Strips trailing/inline parenthetical boilerplate from soundtrack titles,
# e.g. "Wicked (Original Broadway Cast Recording)" -> "Wicked".
_BOILERPLATE_PAREN = re.compile(r"\s*\([^)]*\)")

# A subtitle after ": " or " - " that only says what kind of album it is:
# "The Lion King: Original Motion Picture Soundtrack" -> "The Lion King".
# Only these phrases go; "Spider-Man: Turn Off the Dark" keeps its colon.
_ALBUM_KIND = (
    r"(?:the\s+)?"
    r"(?:(?:original|motion\s+picture|film|movie|television|tv|broadway|"
    r"off-broadway|london|west\s+end|cast|studio|musical|\d{4}|season\s+\w+)"
    r"\s+)*"
    r"(?:cast\s+)?(?:soundtrack|recording|album|score|cast)(?:\s+album)?"
)
_BOILERPLATE_SUBTITLE = re.compile(
    r"\s*(?::|\s-)\s+(?:"
    + _ALBUM_KIND
    + r"|(?:original\s+)?(?:music|songs|soundtrack)(?:\s+album)?\s+from\s+"
    r"(?:and\s+inspired\s+by\s+)?"
    r"the\s+(?:original\s+)?(?:motion\s+picture|film|movie|musical)"
    r"(?:\s+soundtrack)?"
    r")\s*$",
    re.IGNORECASE,
)


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
    """Remove the parentheticals and album-kind subtitle from a soundtrack title."""
    title = _BOILERPLATE_PAREN.sub("", title).strip()
    return _BOILERPLATE_SUBTITLE.sub("", title).strip()


def _various_artists(artist_credit_list: list) -> bool:
    """A release credited to MusicBrainz's "Various Artists"."""
    return any(
        (ac.get("artist") or {}).get("id") == _VARIOUS_ARTISTS_ID
        or _is_placeholder(ac.get("name") or "")
        for ac in artist_credit_list
    )


def _extract_show_name(data: dict) -> str | None:
    """The show a recording was written for, from its releases; None if none.

    A recording is from a show when it's on the show's album: a soundtrack
    album (MusicBrainz files Broadway cast albums as soundtracks too) that
    came out no later than the year the recording first did. A licensed song
    was released years earlier on the artist's own album, so a later movie
    soundtrack doesn't count. Years rather than dates, so a lead single out
    weeks before the album still counts. An album that came out earlier
    counts: a recording added to a later edition of the show's album (a
    remake with a new guest) was made for the show.

    Not every soundtrack is a show's. Singles are named after the song, and
    compilations and "Various Artists" albums gather songs for a film, game
    or TV series rather than from a musical; those don't count. A musical's
    album is credited to its composer or cast. Some film musicals are
    credited to Various Artists and are missed; their show is set by hand.

    Of the albums that qualify, the one out on the recording's first release
    date wins (the original over a same-year translated edition), then the
    earliest.
    """
    first_released = data.get("first-release-date") or ""
    if len(first_released) < 4:
        return None

    candidates = {}
    for release in data.get("releases", []):
        rg = release.get("release-group") or {}
        secondary_types = rg.get("secondary-types") or []
        rg_year = (rg.get("first-release-date") or "")[:4]
        if (
            rg.get("primary-type") == "Album"
            and "Soundtrack" in secondary_types
            and "Compilation" not in secondary_types
            and len(rg_year) == 4
            and rg_year <= first_released[:4]
            and not _various_artists(release.get("artist-credit") or [])
        ):
            candidates[rg.get("id") or rg.get("title")] = rg

    def preference(rg: dict) -> tuple:
        rg_date = rg.get("first-release-date") or ""
        return (
            rg_date != first_released,
            # A date without a month or day sorts after the dated ones
            rg_date.ljust(10, "~"),
        )

    for rg in sorted(candidates.values(), key=preference):
        show_name = _strip_show_name_boilerplate(rg.get("title") or "")
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
) -> tuple[str | None, list[ArtistCredit] | None] | None:
    """Return (show_name, artist_credits) for a recording in a single request.

    Both values come off the same /recording resource, so they are fetched
    together — asking twice would double both the round trips and the
    rate-limit sleep for no benefit. Either element is None when absent
    from the response. The whole result is None if the lookup fails, so a
    failure isn't mistaken for a recording from no show.
    """
    data = _fetch(
        f"recording/{recording_id}",
        {"inc": "releases release-groups artist-credits"},
        cache_dir,
    )
    if data is None:
        return None

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
