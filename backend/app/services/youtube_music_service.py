import logging
from typing import Any, Dict, List

try:
    from ytmusicapi import YTMusic
except ImportError:
    YTMusic = None  # Will raise in __init__ if not installed

logger = logging.getLogger(__name__)


class YouTubeMusicService:
    """Service for searching official audio tracks on YouTube Music."""

    def __init__(self):
        if YTMusic is None:
            logger.error(
                "ytmusicapi is not installed. Please install it in your environment."
            )
            raise ImportError("ytmusicapi is required for YouTubeMusicService.")
        self.ytmusic = YTMusic()

    def search_songs(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search YouTube Music for official audio tracks (type 'song')."""
        try:
            logger.info("Searching YouTube Music for query: %s", query)
            results = self.ytmusic.search(query, filter="songs", limit=limit)
            songs = []
            for item in results:
                if item.get("resultType") == "song" and item.get("videoId"):
                    songs.append(
                        {
                            "videoId": item["videoId"],
                            "title": item.get("title"),
                            "artist": item.get("artists", [{}])[0].get("name"),
                            "duration": item.get("duration"),
                            "album": item.get("album", {}).get("name"),
                            "thumbnails": item.get("thumbnails", []),
                        }
                    )
            logger.info(
                "Found %d official audio tracks for query: %s", len(songs), query
            )
            return songs
        except Exception as e:
            logger.error("YouTube Music search failed: %s", e, exc_info=True)
            raise
