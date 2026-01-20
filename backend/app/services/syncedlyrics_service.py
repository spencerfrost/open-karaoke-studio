import logging
from typing import Any, Dict, List, Optional
import syncedlyrics
from app.exceptions import ServiceError

logger = logging.getLogger(__name__)


class SyncedLyricsService:
    """Alternative lyrics provider using syncedlyrics library"""

    def __init__(self):
        # Default providers (excludes broken ones like Deezer/Lyricsify)
        self.providers = ["Musixmatch", "Lrclib", "NetEase", "Megalobiz"]

    def search_lyrics(self, query: str) -> List[Dict[str, Any]]:
        """
        Search using syncedlyrics library with single query string.
        Returns list of normalized results matching LyricsResult format.
        
        Searches for synced lyrics first, falls back to plain lyrics if none available.
        Note: syncedlyrics returns a single string (not a list), so we wrap it.
        """
        try:
            logger.debug(f"syncedlyrics search query: {query}")

            # First try to get synced lyrics (with all providers)
            synced_result = None
            plain_result = None
            
            try:
                synced_result = syncedlyrics.search(
                    query,
                    synced_only=True,
                    providers=self.providers
                )
            except Exception as e:
                logger.debug(f"Synced lyrics search failed: {e}")

            # If no synced lyrics, try to get plain lyrics as fallback
            if not synced_result:
                try:
                    plain_result = syncedlyrics.search(
                        query,
                        plain_only=True,
                        providers=self.providers
                    )
                except Exception as e:
                    logger.debug(f"Plain lyrics search failed: {e}")

            # Normalize to LyricsResult format
            if synced_result or plain_result:
                result = {
                    "id": None,  # syncedlyrics doesn't provide IDs
                    "name": query,
                    "trackName": None,  # Parsed from query if needed
                    "artistName": None,
                    "albumName": None,
                    "duration": None,
                    "instrumental": False,
                    "plainLyrics": plain_result,
                    "syncedLyrics": synced_result,
                }
                logger.info(f"syncedlyrics found lyrics for: {query}")
                return [result]

            logger.info(f"No lyrics found via syncedlyrics for: {query}")
            return []

        except Exception as e:
            logger.error(f"syncedlyrics search error: {e}", exc_info=True)
            raise ServiceError(f"Failed to search syncedlyrics: {e}")

    def search_lyrics_structured(
        self, params: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Search using structured parameters (track_name, artist_name, album_name).
        Converts to query string for syncedlyrics.
        """
        # Extract and construct query
        track_name = params.get("track_name", "")
        artist_name = params.get("artist_name", "")
        album_name = params.get("album_name", "")

        query_parts = [track_name, artist_name]
        query = " ".join(filter(None, query_parts))

        if not query:
            logger.warning("Empty query in structured search")
            return []

        results = self.search_lyrics(query)

        # Enhance results with structured metadata
        if results:
            results[0].update({
                "trackName": track_name,
                "artistName": artist_name,
                "albumName": album_name,
            })

        return results
