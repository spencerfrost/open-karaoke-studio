"""
YouTube Music search and browse for the add-song flow.

Every song this service returns has the same shape, wherever it came from
(search, an artist's popular songs, an album's tracks): see `_song`.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from cachetools import TTLCache

from app.exceptions import NotFoundError
from app.services.artist_parsing import artist_credit
from app.utils.song_titles import normalize, song_key

try:
    from ytmusicapi import YTMusic
except ImportError:
    YTMusic = None  # Will raise in __init__ if not installed

logger = logging.getLogger(__name__)

# Module-level caches with 15-minute TTL
_artist_cache: TTLCache = TTLCache(maxsize=100, ttl=900)
_album_cache: TTLCache = TTLCache(maxsize=200, ttl=900)
# Search and suggestion cache with 5-minute TTL
_search_cache: TTLCache = TTLCache(maxsize=500, ttl=300)

# Popular songs shown on the artist screen before "Show all popular songs"
TOP_SONGS_SHOWN = 5


def _duration_seconds(item: Dict) -> Optional[int]:
    """An item's length: ytmusicapi's duration_seconds, else parsed from "m:ss"."""
    if item.get("duration_seconds"):
        return int(item["duration_seconds"])
    text = item.get("duration") or ""
    try:
        seconds = 0
        for part in text.split(":"):
            seconds = seconds * 60 + int(part)
        return seconds or None
    except ValueError:
        return None


def _song(
    item: Dict,
    *,
    album: Optional[Dict] = None,
    thumbnails: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """One song in the shape the add-song flow uses.

    `artists` keeps every credited artist with their ids; `artist` is the same
    names as the one credit line a library song stores. Album tracks pass the
    album and its cover, since ytmusicapi leaves them off each track.
    """
    artists = [
        {"name": a["name"], "id": a.get("id")}
        for a in item.get("artists") or []
        if a and a.get("name")
    ]
    if album is None:
        album = item.get("album") if isinstance(item.get("album"), dict) else {}
    return {
        "videoId": item.get("videoId"),
        "title": item.get("title"),
        "artists": artists,
        "artist": artist_credit([a["name"] for a in artists]) or None,
        "album": album.get("name"),
        "albumId": album.get("id"),
        "durationSeconds": _duration_seconds(item),
        "isExplicit": bool(item.get("isExplicit")),
        "thumbnails": thumbnails or item.get("thumbnails") or [],
    }


def _release(item: Dict, kind: str) -> Dict[str, Any]:
    return {
        "browseId": item.get("browseId"),
        "title": item.get("title"),
        "year": item.get("year"),
        "type": kind,
        "thumbnails": item.get("thumbnails", []),
    }


def _distinct_releases(releases: List[Dict]) -> List[Dict]:
    """One release per title: YouTube Music can list an album twice."""
    seen = set()
    distinct = []
    for release in releases:
        key = (release.get("title") or "").strip().lower()
        if key in seen:
            continue
        seen.add(key)
        distinct.append(release)
    return distinct


# "Sped Up" and "Slowed Down" versions count: remixes in all but name
_REMIX_WORDS = frozenset({"remix", "remixes", "remixed", "reblend", "sped", "slowed"})


def _is_remix_release(release: Dict) -> bool:
    """A remix, not an album or single: "Supersonic (Remixes)", "Remixed",
    "Little L (Sped Up Version)"."""
    return bool(_REMIX_WORDS & set(normalize(release.get("title") or "").split()))


def _oldest_first(releases: List[Dict]) -> List[Dict]:
    """By year, oldest first; releases without a year go last, in their order."""

    def year(release: Dict) -> int:
        value = release.get("year") or ""
        return int(value) if value.isdigit() else 10_000

    return sorted(releases, key=year)


def group_search_songs(songs: List[Dict]) -> Dict[str, Any]:
    """Split song results into the best match, its other versions, and the rest.

    YouTube Music ranks the original recording first, so the first result is
    the best match. Results sharing its song key (covers, live takes, remasters,
    the same song on a compilation) are other versions of it; everything else
    is a different song.
    """
    if not songs:
        return {"bestMatch": None, "otherVersions": [], "otherSongs": []}

    best, rest = songs[0], songs[1:]
    best_key = song_key(best.get("title") or "")
    other_versions = [s for s in rest if song_key(s.get("title") or "") == best_key]
    other_songs = [s for s in rest if song_key(s.get("title") or "") != best_key]
    return {
        "bestMatch": best,
        "otherVersions": other_versions,
        "otherSongs": other_songs,
    }


class YoutubeMusicService:
    """Service for searching official audio tracks on YouTube Music."""

    def __init__(self):
        if YTMusic is None:
            logger.error(
                "ytmusicapi is not installed. Please install it in your environment."
            )
            raise ImportError("ytmusicapi is required for YoutubeMusicService.")
        self.ytmusic = YTMusic()

    def _normalize_song_results(self, raw_results: List[Dict]) -> List[Dict[str, Any]]:
        """Normalize raw song search results from ytmusicapi."""
        return [
            _song(item)
            for item in raw_results
            if item.get("resultType") == "song" and item.get("videoId")
        ]

    def _normalize_artist_results(
        self, raw_results: List[Dict], max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """Normalize raw artist search results from ytmusicapi.

        Args:
            raw_results: Raw search results from ytmusicapi
            max_results: Maximum number of artists to return (default 3)
        """
        artists = []
        for item in raw_results:
            if item.get("resultType") == "artist" and item.get("browseId"):
                # ytmusicapi may use "artist" or "name" field for artist name
                artist_name = item.get("artist") or item.get("name") or "Unknown Artist"
                artists.append(
                    {
                        "browseId": item["browseId"],
                        "name": artist_name,
                        "subscribers": item.get("subscribers"),
                        "thumbnails": item.get("thumbnails", []),
                    }
                )
                # Stop after collecting max_results
                if len(artists) >= max_results:
                    break
        return artists

    def search(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """Search YouTube Music for artists (up to 3) and songs in parallel.

        `topArtistId` is set when YouTube Music's own top result for the query
        is an artist: "queen" is, "bohemian rhapsody" isn't, though an artist
        by that name exists. The add flow opens that artist for a picked
        suggestion.
        """
        cache_key = f"search:{query}:{limit}"
        if cache_key in _search_cache:
            logger.info("Cache hit for search: %s", query)
            return _search_cache[cache_key]

        try:
            logger.info("Searching YouTube Music for query: %s", query)

            with ThreadPoolExecutor(max_workers=3) as executor:
                artist_future = executor.submit(
                    self.ytmusic.search, query, filter="artists", limit=3
                )
                song_future = executor.submit(
                    self.ytmusic.search, query, filter="songs", limit=limit
                )
                top_future = executor.submit(self._top_artist_id, query)

                artist_results = artist_future.result()
                song_results = song_future.result()
                top_artist_id = top_future.result()

            artists = self._normalize_artist_results(artist_results, max_results=3)
            songs = self._normalize_song_results(song_results)

            result = {"artists": artists, "songs": songs, "topArtistId": top_artist_id}
            _search_cache[cache_key] = result

            logger.info(
                "Found %d artists and %d songs for query: %s",
                len(artists),
                len(songs),
                query,
            )
            return result

        except Exception as e:
            logger.error("YouTube Music search failed: %s", e, exc_info=True)
            raise

    def _top_artist_id(self, query: str) -> Optional[str]:
        """The artist's id when the unfiltered search's top result is an artist.

        Only a hint: when it fails, the search goes on without it.
        """
        try:
            results = self.ytmusic.search(query, limit=1)
        except Exception as e:
            logger.warning("Top result lookup failed for %r: %s", query, e)
            return None
        top = results[0] if results else {}
        if top.get("category") != "Top result" or top.get("resultType") != "artist":
            return None
        artists = top.get("artists") or []
        return top.get("browseId") or (artists[0].get("id") if artists else None)

    def get_suggestions(self, query: str) -> List[str]:
        """Plain search suggestions for what's been typed so far."""
        cache_key = f"suggest:{query}"
        if cache_key in _search_cache:
            return _search_cache[cache_key]

        try:
            suggestions = [s for s in self.ytmusic.get_search_suggestions(query) if s]
        except Exception as e:
            logger.error(
                "YouTube Music suggestions failed for %r: %s", query, e, exc_info=True
            )
            raise

        _search_cache[cache_key] = suggestions
        return suggestions

    def get_all_artist_releases(
        self, channel_id: str, params: str
    ) -> List[Dict[str, Any]]:
        """Every album or single behind an artist page's "See all" link."""
        cache_key = f"releases:{channel_id}:{params}"
        if cache_key in _artist_cache:
            logger.info("Cache hit for releases: %s", channel_id)
            return _artist_cache[cache_key]

        try:
            logger.info("Fetching all releases for channel: %s", channel_id)
            raw = self.ytmusic.get_artist_albums(channel_id, params)
            result = _distinct_releases(
                [_release(item, (item.get("type") or "album").lower()) for item in raw]
            )
            _artist_cache[cache_key] = result
            logger.info("Fetched %d releases for channel: %s", len(result), channel_id)
            return result
        except Exception as e:
            logger.error(
                "Failed to get releases for channel %s: %s",
                channel_id,
                e,
                exc_info=True,
            )
            raise

    def _raw_artist(self, artist_id: str) -> Dict:
        """ytmusicapi's artist page, cached. NotFoundError for an unknown id."""
        cache_key = f"raw:{artist_id}"
        if cache_key in _artist_cache:
            return _artist_cache[cache_key]

        logger.info("Fetching artist from YouTube Music: %s", artist_id)
        try:
            raw = self.ytmusic.get_artist(artist_id)
        except KeyError as e:
            # ytmusicapi can't find the page's contents: there's no such artist.
            raise NotFoundError(f"No YouTube Music artist {artist_id}") from e
        _artist_cache[cache_key] = raw
        return raw

    def get_artist_songs(self, artist_id: str) -> List[Dict[str, Any]]:
        """Every one of the artist's popular songs, in YouTube Music's order.

        The artist page shows five; the full list is the playlist behind its
        "Show all" link. When that playlist can't be read, the five will do.
        """
        cache_key = f"songs:{artist_id}"
        if cache_key in _artist_cache:
            return _artist_cache[cache_key]

        songs_data = self._raw_artist(artist_id).get("songs") or {}
        raw_songs = songs_data.get("results") or []
        if songs_data.get("browseId"):
            try:
                playlist = self.ytmusic.get_playlist(songs_data["browseId"], limit=None)
                raw_songs = playlist.get("tracks") or raw_songs
            except Exception as e:
                logger.warning(
                    "Popular songs playlist failed for %s, using the artist page's: %s",
                    artist_id,
                    e,
                )

        songs = [_song(item) for item in raw_songs if item.get("videoId")]
        _artist_cache[cache_key] = songs
        logger.info("Fetched %d popular songs for artist %s", len(songs), artist_id)
        return songs

    def _artist_releases(
        self, artist_id: str, raw: Dict, section_key: str
    ) -> List[Dict[str, Any]]:
        """Every album, or every single, oldest first, like a discography.

        The artist page lists only the newest few, so the rest are fetched up
        front rather than behind a "See all". When that fails, the page's few
        will do. Remix collections are among them; get_artist sets those apart.
        """
        section = raw.get(section_key) or {}
        kind = "single" if section_key == "singles" else "album"
        releases = [_release(item, kind) for item in section.get("results", [])]
        if section.get("params"):
            try:
                releases = self.get_all_artist_releases(
                    section.get("browseId") or artist_id, section["params"]
                )
            except Exception as e:
                logger.warning(
                    "All %s failed for %s, using the artist page's: %s",
                    section_key,
                    artist_id,
                    e,
                )
        return _oldest_first(_distinct_releases(releases))

    def get_artist(self, artist_id: str) -> Dict[str, Any]:
        """Artist info, the first popular songs, and every album, single and
        remix collection."""
        try:
            raw = self._raw_artist(artist_id)
            with ThreadPoolExecutor(max_workers=3) as executor:
                songs_future = executor.submit(self.get_artist_songs, artist_id)
                albums_future = executor.submit(
                    self._artist_releases, artist_id, raw, "albums"
                )
                singles_future = executor.submit(
                    self._artist_releases, artist_id, raw, "singles"
                )
                songs = songs_future.result()
                all_albums = albums_future.result()
                all_singles = singles_future.result()
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to get artist %s: %s", artist_id, e, exc_info=True)
            raise

        # Remix collections fill YouTube Music's album list (11 of Jamiroquai's
        # 24) and its singles; they go last, so the albums and singles read as
        # a discography.
        albums = [r for r in all_albums if not _is_remix_release(r)]
        singles = [r for r in all_singles if not _is_remix_release(r)]
        remixes = _oldest_first(
            _distinct_releases(
                [r for r in all_albums + all_singles if _is_remix_release(r)]
            )
        )

        return {
            "artist": {
                "id": artist_id,
                "name": raw.get("name"),
                "thumbnails": raw.get("thumbnails", []),
                "description": raw.get("description"),
                "subscribers": raw.get("subscribers"),
            },
            "topSongs": songs[:TOP_SONGS_SHOWN],
            "hasMoreSongs": len(songs) > TOP_SONGS_SHOWN,
            "albums": albums,
            "singles": singles,
            "remixes": remixes,
        }

    def get_album_tracks(self, album_id: str) -> Dict[str, Any]:
        """An album's info and tracks. NotFoundError for an unknown id."""
        if album_id in _album_cache:
            logger.info("Cache hit for album: %s", album_id)
            return _album_cache[album_id]

        try:
            logger.info("Fetching album from YouTube Music: %s", album_id)
            raw = self.ytmusic.get_album(album_id)
        except KeyError as e:
            # ytmusicapi can't find the page's contents: there's no such album.
            raise NotFoundError(f"No YouTube Music album {album_id}") from e
        except Exception as e:
            logger.error("Failed to get album %s: %s", album_id, e, exc_info=True)
            raise

        album_thumbnails = raw.get("thumbnails", [])
        album_title = raw.get("title")
        album_ref = {"name": album_title, "id": album_id}
        album_artists = [
            {"name": a["name"], "id": a.get("id")}
            for a in raw.get("artists") or []
            if a and a.get("name")
        ]

        tracks = []
        for number, track in enumerate(raw.get("tracks", []), start=1):
            song = _song(track, album=album_ref, thumbnails=album_thumbnails)
            # trackNumber is often missing; the list is in track order anyway.
            song["trackNumber"] = track.get("trackNumber") or number
            tracks.append(song)

        result = {
            "album": {
                "browseId": album_id,
                "title": album_title,
                "artists": album_artists,
                "type": raw.get("type"),
                "year": raw.get("year"),
                "thumbnails": album_thumbnails,
                "trackCount": len(tracks),
            },
            "tracks": tracks,
        }

        _album_cache[album_id] = result
        logger.info("Fetched album %s with %d tracks", album_title, len(tracks))
        return result
