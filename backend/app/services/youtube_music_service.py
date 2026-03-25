import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from cachetools import TTLCache

try:
    from ytmusicapi import YTMusic
except ImportError:
    YTMusic = None  # Will raise in __init__ if not installed

logger = logging.getLogger(__name__)

# Module-level caches with 15-minute TTL
_artist_cache: TTLCache = TTLCache(maxsize=100, ttl=900)
_album_cache: TTLCache = TTLCache(maxsize=200, ttl=900)
# Search cache with 5-minute TTL
_search_cache: TTLCache = TTLCache(maxsize=500, ttl=300)


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
        songs = []
        for item in raw_results:
            if item.get("resultType") == "song" and item.get("videoId"):
                artists = item.get("artists", [{}])
                primary_artist = artists[0] if artists else {}
                songs.append(
                    {
                        "videoId": item["videoId"],
                        "title": item.get("title"),
                        "artist": primary_artist.get("name"),
                        "artistId": primary_artist.get("id"),
                        "duration": item.get("duration"),
                        "album": item.get("album", {}).get("name"),
                        "thumbnails": item.get("thumbnails", []),
                    }
                )
        return songs

    def _normalize_artist_results(self, raw_results: List[Dict], max_results: int = 3) -> List[Dict[str, Any]]:
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

    def search_combined(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search YouTube Music for both artists and songs in parallel."""
        # Check cache first
        cache_key = f"search:{query}:{limit}"
        if cache_key in _search_cache:
            logger.info("Cache hit for search: %s", query)
            return _search_cache[cache_key]

        try:
            logger.info("Searching YouTube Music for query: %s", query)

            # Limit artists to 3 results max
            artist_limit = min(3, limit // 2)

            # Parallel search for artists and songs using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=2) as executor:
                artist_future = executor.submit(
                    self.ytmusic.search, query, filter="artists", limit=artist_limit
                )
                song_future = executor.submit(
                    self.ytmusic.search, query, filter="songs", limit=limit
                )

                artist_results = artist_future.result()
                song_results = song_future.result()

            # Normalize results (limit artists to 3)
            artists = self._normalize_artist_results(artist_results, max_results=3)
            songs = self._normalize_song_results(song_results)

            result = {"artists": artists, "songs": songs}

            # Cache the result
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

    def search_songs(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search YouTube Music for official audio tracks (type 'song').

        DEPRECATED: Use search_combined() instead for better performance.
        This method is kept for backward compatibility.
        """
        try:
            logger.info("Searching YouTube Music for query: %s", query)
            results = self.ytmusic.search(query, filter="songs", limit=limit)
            songs = self._normalize_song_results(results)
            logger.info(
                "Found %d official audio tracks for query: %s", len(songs), query
            )
            return songs
        except Exception as e:
            logger.error("YouTube Music search failed: %s", e, exc_info=True)
            raise


    def _get_song_duration(self, video_id: str) -> Optional[str]:
        """Fetch duration for a song using get_song API.
        
        Returns duration in mm:ss format, or None if unavailable.
        """
        try:
            song_info = self.ytmusic.get_song(video_id)
            video_details = song_info.get("videoDetails", {})
            length_seconds = video_details.get("lengthSeconds")
            
            if length_seconds:
                seconds = int(length_seconds)
                minutes = seconds // 60
                remaining_seconds = seconds % 60
                return f"{minutes}:{remaining_seconds:02d}"
            return None
        except Exception as e:
            logger.warning("Failed to get duration for video %s: %s", video_id, e)
            return None

    def get_all_artist_releases(self, channel_id: str, params: str) -> List[Dict[str, Any]]:
        """Fetch all albums or singles for an artist using ytmusicapi pagination params."""
        cache_key = f"releases:{channel_id}:{params}"
        if cache_key in _artist_cache:
            logger.info("Cache hit for releases: %s", channel_id)
            return _artist_cache[cache_key]

        try:
            logger.info("Fetching all releases for channel: %s", channel_id)
            raw = self.ytmusic.get_artist_albums(channel_id, params)
            result = [
                {
                    "browseId": item.get("browseId"),
                    "title": item.get("title"),
                    "year": item.get("year"),
                    "type": item.get("type", "album").lower(),
                    "thumbnails": item.get("thumbnails", []),
                }
                for item in raw
            ]
            _artist_cache[cache_key] = result
            logger.info("Fetched %d releases for channel: %s", len(result), channel_id)
            return result
        except Exception as e:
            logger.error("Failed to get releases for channel %s: %s", channel_id, e, exc_info=True)
            raise

    def get_artist(self, artist_id: str, top_songs_limit: int = 12) -> Dict[str, Any]:
        """Get artist info, top songs, and album list."""
        # Check cache first
        cache_key = f"v2:{artist_id}:{top_songs_limit}"
        if cache_key in _artist_cache:
            logger.info("Cache hit for artist: %s", artist_id)
            return _artist_cache[cache_key]

        try:
            logger.info("Fetching artist from YouTube Music: %s", artist_id)
            raw = self.ytmusic.get_artist(artist_id)

            # Normalize top songs
            top_songs = []
            songs_data = raw.get("songs", {})
            songs_browse_id = songs_data.get("browseId")
            raw_songs = []
            
            # Try to fetch full playlist if browseId is available
            if songs_browse_id:
                try:
                    playlist = self.ytmusic.get_playlist(songs_browse_id, limit=top_songs_limit)
                    raw_songs = playlist.get("tracks", [])[:top_songs_limit]
                    logger.info("Fetched %d top songs via playlist for artist %s", len(raw_songs), artist_id)
                except Exception as e:
                    logger.warning("Playlist fetch failed for %s, falling back to results: %s", artist_id, e)
                    raw_songs = songs_data.get("results", [])[:top_songs_limit]
            else:
                raw_songs = songs_data.get("results", [])[:top_songs_limit]
            
            for song in raw_songs:
                video_id = song.get("videoId")
                duration = song.get("duration")
                
                # Only call _get_song_duration for get_artist() results
                # (playlist tracks from get_playlist() already have duration)
                if not duration and video_id and not songs_browse_id:
                    duration = self._get_song_duration(video_id)
                
                top_songs.append(
                    {
                        "videoId": video_id,
                        "title": song.get("title"),
                        "artist": raw.get("name"),
                        "artistId": artist_id,
                        "album": song.get("album", {}).get("name")
                        if isinstance(song.get("album"), dict)
                        else song.get("album"),
                        "duration": duration,
                        "thumbnails": song.get("thumbnails", []),
                    }
                )

            # Normalize albums and singles as separate lists
            albums: List[Dict] = []
            singles: List[Dict] = []
            albums_more: Optional[Dict] = None
            singles_more: Optional[Dict] = None

            for section_key, dest_list in [("albums", albums), ("singles", singles)]:
                section_data = raw.get(section_key, {})
                for item in section_data.get("results", []):
                    dest_list.append(
                        {
                            "browseId": item.get("browseId"),
                            "title": item.get("title"),
                            "year": item.get("year"),
                            "type": "single" if section_key == "singles" else "album",
                            "thumbnails": item.get("thumbnails", []),
                        }
                    )
                # Capture pagination params when YouTube Music has more results
                if section_data.get("params"):
                    pagination = {
                        "channelId": section_data.get("browseId"),
                        "params": section_data.get("params"),
                    }
                    if section_key == "albums":
                        albums_more = pagination
                    else:
                        singles_more = pagination

            result = {
                "artist": {
                    "id": artist_id,
                    "name": raw.get("name"),
                    "thumbnails": raw.get("thumbnails", []),
                    "description": raw.get("description"),
                    "subscribers": raw.get("subscribers"),
                },
                "topSongs": top_songs,
                "albums": albums,
                "singles": singles,
                "albumsMore": albums_more,
                "singlesMore": singles_more,
            }

            # Cache the result
            _artist_cache[cache_key] = result
            logger.info(
                "Fetched artist %s with %d top songs, %d albums, %d singles",
                raw.get("name"),
                len(top_songs),
                len(albums),
                len(singles),
            )
            return result

        except Exception as e:
            logger.error("Failed to get artist %s: %s", artist_id, e, exc_info=True)
            raise

    def get_album_tracks(self, album_id: str) -> Dict[str, Any]:
        """Get all tracks from an album."""
        # Check cache first
        if album_id in _album_cache:
            logger.info("Cache hit for album: %s", album_id)
            return _album_cache[album_id]

        try:
            logger.info("Fetching album from YouTube Music: %s", album_id)
            raw = self.ytmusic.get_album(album_id)

            album_thumbnails = raw.get("thumbnails", [])
            album_title = raw.get("title")

            tracks = []
            for track in raw.get("tracks", []):
                artists = track.get("artists", [{}])
                primary_artist = artists[0] if artists else {}
                tracks.append(
                    {
                        "videoId": track.get("videoId"),
                        "title": track.get("title"),
                        "artist": primary_artist.get("name"),
                        "artistId": primary_artist.get("id"),
                        "album": album_title,
                        "duration": track.get("duration"),
                        "trackNumber": track.get("trackNumber"),
                        "thumbnails": album_thumbnails,
                        "isExplicit": track.get("isExplicit", False),
                    }
                )

            result = {
                "album": {
                    "browseId": album_id,
                    "title": album_title,
                    "artist": raw.get("artists", [{}])[0].get("name")
                    if raw.get("artists")
                    else None,
                    "year": raw.get("year"),
                    "thumbnails": album_thumbnails,
                    "trackCount": len(tracks),
                },
                "tracks": tracks,
            }

            # Cache the result
            _album_cache[album_id] = result
            logger.info(
                "Fetched album %s with %d tracks", album_title, len(tracks)
            )
            return result

        except Exception as e:
            logger.error("Failed to get album %s: %s", album_id, e, exc_info=True)
            raise
