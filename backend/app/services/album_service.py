"""
Album service: find a song's album and cover, and save them together.

One lookup finds the album name, its cover and the explicit flag, and they're
written in one transaction, so the name a song shows and the cover beside it
always come from the same release.

    1. YouTube Music: the album of the exact video the song was downloaded
       from (right by construction). Plain uploads aren't on an album.
    2. Deezer: a title + artist search, accepted only when the artist and
       title match (see deezer_result_matches).
    3. Nothing: the song keeps its YouTube thumbnail and is marked checked.

Songs whose album a person set (album_hand_set_at) are never looked up.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal, Optional

import requests

from app.db.models.song import DbSong
from app.utils.clock import utc_now

logger = logging.getLogger(__name__)

AlbumOutcome = Literal["found", "no_cover", "not_found", "hand_set", "error"]

_DEEZER_SEARCH = "https://api.deezer.com/search"
_DEEZER_ALBUM = "https://api.deezer.com/album/{id}"
_TIMEOUT = 10
# Square, 1200px: "-s" keeps a non-square original from being stretched.
_YTMUSIC_ART_SIZE = "=w1200-h1200-s-l90-rj"
_YTMUSIC_SIZE_SUFFIX = re.compile(r"=w\d+-h\d+[^/]*$")


class AlbumLookupError(Exception):
    """A source couldn't be reached. Nothing is saved; the next run asks again."""


@dataclass(frozen=True)
class AlbumMatch:
    source: Literal["ytmusic", "deezer"]
    source_id: str
    title: str
    year: Optional[str]
    cover_url: Optional[str]
    # None when the source didn't say; a song's flag is left as it was then
    explicit: Optional[bool]


# --------------------------------------------------------------------------
# Lookup
# --------------------------------------------------------------------------


def find_album(song: DbSong) -> AlbumMatch | None:
    """The album of `song`'s audio, or None when no source has it.

    Raises AlbumLookupError when a source couldn't be reached.
    """
    if song.video_id:
        match = _from_youtube_music(song.video_id, song.title, song.artist)
        if match:
            return match
    if song.title and song.artist:
        return _from_deezer(song.title, primary_artist_name(song))
    return None


def primary_artist_name(song: DbSong) -> str:
    """The song's first primary credit, or its artist string before credits exist."""
    primaries = sorted(
        (sa for sa in song.song_artists if sa.role == "primary"),
        key=lambda sa: sa.display_order,
    )
    for credit in primaries:
        artist = credit.artist_rel
        name = artist and (artist.display_name or artist.name)
        if name:
            return name
    return song.artist


def _youtube_music():
    from ytmusicapi import YTMusic

    return YTMusic()


def _from_youtube_music(video_id: str, title: str, artist: str) -> AlbumMatch | None:
    """The album YouTube Music files this exact video under."""
    from ytmusicapi.exceptions import YTMusicServerError

    ytmusic = _youtube_music()
    try:
        tracks = ytmusic.get_watch_playlist(video_id, limit=1).get("tracks") or []
    except YTMusicServerError as e:
        # A removed or private video has no watch page.
        if "No content returned" in str(e):
            logger.info("YouTube Music has no video %s", video_id)
            return None
        raise AlbumLookupError(f"YouTube Music: {e}") from e
    except Exception as e:
        raise AlbumLookupError(f"YouTube Music: {e}") from e

    track = tracks[0] if tracks else {}
    album = track.get("album") or {}
    if track.get("videoId") != video_id or not album.get("id"):
        # Music videos and plain uploads aren't on an album.
        return None

    thumbnails = track.get("thumbnail") or []
    cover_url = None
    if thumbnails:
        cover_url = _YTMUSIC_SIZE_SUFFIX.sub(_YTMUSIC_ART_SIZE, thumbnails[-1]["url"])

    return AlbumMatch(
        source="ytmusic",
        source_id=album["id"],
        title=album.get("name") or title,
        year=_year(track.get("year")),
        cover_url=cover_url,
        explicit=_youtube_music_explicit(ytmusic, video_id, title, artist),
    )


def _youtube_music_explicit(ytmusic, video_id: str, title: str, artist: str):
    """The explicit flag of this video. Only search results carry it."""
    try:
        results = ytmusic.search(f"{artist} {title}", filter="songs", limit=20)
    except Exception:
        logger.warning("YouTube Music search failed for %s", video_id, exc_info=True)
        return None
    for result in results:
        if result.get("videoId") == video_id:
            explicit = result.get("isExplicit")
            return explicit if isinstance(explicit, bool) else None
    return None


def _from_deezer(title: str, artist: str) -> AlbumMatch | None:
    """The first Deezer result whose artist and title match the song's."""
    # Deezer's artist:"…" filter returns nothing (2026-10), so this is a plain
    # search and the match rules do the filtering.
    data = _deezer_get(_DEEZER_SEARCH, {"q": f"{artist} {title}", "limit": 25})
    for item in data.get("data", []):
        if not deezer_result_matches(item, title=title, artist=artist):
            continue
        album = item.get("album") or {}
        if not album.get("id"):
            continue
        return AlbumMatch(
            source="deezer",
            source_id=str(album["id"]),
            title=album.get("title") or title,
            year=_deezer_album_year(album["id"]),
            cover_url=_deezer_cover(album.get("cover_xl")),
            explicit=item.get("explicit_lyrics"),
        )
    return None


def _deezer_get(url: str, params: dict | None = None) -> dict:
    try:
        response = requests.get(url, params=params, timeout=_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as e:
        raise AlbumLookupError(f"Deezer: {e}") from e
    error = data.get("error")
    # Code 4 is Deezer's quota error; 800 ("no data") is an unknown id.
    if error and error.get("code") != 800:
        raise AlbumLookupError(f"Deezer: {error}")
    return data


def _deezer_album_year(album_id) -> Optional[str]:
    try:
        data = _deezer_get(_DEEZER_ALBUM.format(id=album_id))
    except AlbumLookupError:
        logger.warning("Deezer album %s lookup failed", album_id, exc_info=True)
        return None
    return _year(data.get("release_date"))


def _deezer_cover(url: Optional[str]) -> Optional[str]:
    # An album without art has an empty image hash: ".../cover//1000x1000-…".
    if not url or "/cover//" in url:
        return None
    return url


def _year(value) -> Optional[str]:
    text = str(value or "")[:4]
    return text if len(text) == 4 and text.isdigit() else None


# --------------------------------------------------------------------------
# Deezer match rules
# --------------------------------------------------------------------------

# Markers that make a different recording. A song title carrying one needs a
# Deezer title carrying it too.
VERSION_MARKERS = frozenset(
    {"live", "acoustic", "remix", "demo", "edit", "version", "unplugged"}
)
# Of those, the ones a Deezer title can't carry unless the song's does: a
# "Radio Edit" or "Album Version" is the same recording, a live one isn't.
STRICT_MARKERS = frozenset({"live", "acoustic", "remix", "demo", "unplugged"})
# Albums that are someone else's recording of the song.
REJECTED_ALBUM_WORDS = (
    "karaoke",
    "tribute",
    "made famous",
    "in the style of",
    "instrumental",
    "8 bit",
    "8bit",
)

_FEAT_ARTIST = re.compile(r"\s+(feat\.?|ft\.?|featuring|with)\s.*$", re.IGNORECASE)
_FEAT_TITLE = re.compile(r"\s+(feat\.?|ft\.?|featuring)\s.*$", re.IGNORECASE)
_BRACKETED = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")


def normalize(text: str) -> str:
    """Lowercase, no accents or punctuation, "&" as "and", single spaces."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^\w\s]", " ", text).replace("_", " ")
    return " ".join(text.split())


def _artist_key(artist: str) -> str:
    key = normalize(_FEAT_ARTIST.sub("", _BRACKETED.sub("", artist or "")))
    return key[4:] if key.startswith("the ") else key


def _title_key(title: str) -> str:
    return normalize(_FEAT_TITLE.sub("", _BRACKETED.sub("", title or "")))


def _markers(title: str) -> set[str]:
    words = set(normalize(title).split())
    if "remixed" in words:
        words.add("remix")
    return words & VERSION_MARKERS


def deezer_result_matches(item: dict, *, title: str, artist: str) -> bool:
    """Whether a Deezer search result is this song on its own release."""
    deezer_artist = (item.get("artist") or {}).get("name") or ""
    if not _artist_key(artist) or _artist_key(deezer_artist) != _artist_key(artist):
        return False

    deezer_title = item.get("title") or ""
    deezer_short = item.get("title_short") or deezer_title
    if _title_key(deezer_short) != _title_key(title):
        return False

    song_markers = _markers(title)
    deezer_markers = _markers(f"{deezer_title} {item.get('title_version') or ''}")
    if not song_markers <= deezer_markers:
        return False
    if (deezer_markers & STRICT_MARKERS) - song_markers:
        return False

    album_title = normalize((item.get("album") or {}).get("title") or "")
    return not any(word in album_title for word in REJECTED_ALBUM_WORDS)


# --------------------------------------------------------------------------
# Saving
# --------------------------------------------------------------------------


def assign_album(song_id: str, match: AlbumMatch) -> AlbumOutcome:
    """Link the song to the matched album, downloading its cover if needed.

    The song's album name, album link and explicit flag are written in one
    transaction. Returns "found" when the album has a cover, "no_cover" when
    the source has none, "error" when the download failed (the next run tries
    again), or "hand_set" when a person set the album meanwhile.
    """
    from app.db.database import get_db_session
    from app.repositories.album_repository import AlbumRepository

    with get_db_session() as session:
        song = session.get(DbSong, song_id)
        if song is None:
            return "not_found"
        album = AlbumRepository(session).get_or_create(
            source=match.source,
            source_id=match.source_id,
            title=match.title,
            artist_id=song.artist_id,
            release_date=match.year,
        )
        album_id = album.id
        has_cover = bool(album.cover_path)

    cover_path = None
    if not has_cover and match.cover_url:
        cover_path = _download_cover(album_id, match.cover_url)

    with get_db_session() as session:
        from app.db.models.album import DbAlbum

        song = session.get(DbSong, song_id)
        album = session.get(DbAlbum, album_id)
        if song is None or album is None:
            return "not_found"
        if song.album_hand_set_at is not None:
            return "hand_set"
        if cover_path:
            album.cover_path = cover_path
            album.image_status = "found"
        elif not album.cover_path and not match.cover_url:
            album.image_status = "not_found"

        song.album = album.title
        song.album_id = album.id
        if match.explicit is not None:
            song.explicit = match.explicit

        if album.cover_path:
            outcome: AlbumOutcome = "found"
        elif match.cover_url:
            outcome = "error"  # the download failed; a later run tries again
        else:
            outcome = "no_cover"
        song.album_checked_at = utc_now() if outcome == "no_cover" else None
        session.commit()

    logger.info(
        "Album for song %s: %r (%s %s, %s)",
        song_id,
        match.title,
        match.source,
        match.source_id,
        outcome,
    )
    return outcome


def refresh_song_album(song_id: str) -> AlbumOutcome:
    """Look up a song's album and save it. Never touches a hand-set album."""
    from app.db.database import get_db_session

    with get_db_session() as session:
        song = session.get(DbSong, song_id)
        if song is None:
            return "not_found"
        if song.album_hand_set_at is not None:
            return "hand_set"
        try:
            match = find_album(song)
        except AlbumLookupError as e:
            logger.warning("Album lookup failed for song %s: %s", song_id, e)
            return "error"
        if match is None:
            song.album_checked_at = utc_now()
            session.commit()
            logger.info("No album found for song %s", song_id)
            return "not_found"

    return assign_album(song_id, match)


def _download_cover(album_id: int, url: str) -> Optional[str]:
    """Save the cover as covers/album-{id}.jpg. Returns that path, or None."""
    from app.config import get_config

    covers_dir = get_config().library_path / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)
    relative = f"covers/album-{album_id}.jpg"
    dest = covers_dir / f"album-{album_id}.jpg"
    try:
        response = requests.get(url, timeout=_TIMEOUT)
        response.raise_for_status()
        if not response.headers.get("content-type", "").startswith("image/"):
            raise ValueError(f"not an image: {response.headers.get('content-type')}")
        partial = dest.with_suffix(".part")
        partial.write_bytes(response.content)
        partial.replace(dest)
    except Exception as e:
        logger.warning("Cover download failed for album %s: %s", album_id, e)
        return None
    return relative


def delete_unlinked_albums() -> int:
    """Delete albums no song links to, and their cover files. Returns how many."""
    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.album_repository import AlbumRepository

    library = get_config().library_path
    with get_db_session() as session:
        albums = AlbumRepository(session).unlinked()
        for album in albums:
            if album.cover_path:
                (library / album.cover_path).unlink(missing_ok=True)
            session.delete(album)
        session.commit()
    if albums:
        logger.info("Deleted %d albums no song links to", len(albums))
    return len(albums)
