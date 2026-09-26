import logging
from typing import Any, Dict, List, Optional
import syncedlyrics
from app.exceptions import ServiceError

logger = logging.getLogger(__name__)


class SyncedLyricsService:
    """Alternative lyrics provider using syncedlyrics library"""

    # Plain text providers — tried first. Genius gives the best quality text.
    PLAIN_PROVIDERS = ["Genius", "Lrclib"]
    # Synced (LRC) providers — used as fallback when no plain text found.
    SYNCED_PROVIDERS = ["Musixmatch", "Lrclib", "NetEase", "Megalobiz"]

    def __init__(self):
        pass

    def search_lyrics(self, query: str) -> List[Dict[str, Any]]:
        """
        Search using syncedlyrics library with single query string.

        Priority:
          1. Plain lyrics via Genius (highest quality text for alignment)
          2. Plain lyrics via other plain providers (Lrclib)
          3. Synced lyrics (LRC) as fallback

        Returns a list with one normalized result dict, or empty list if nothing found.
        Both plainLyrics and syncedLyrics are populated when available.
        """
        try:
            logger.debug("syncedlyrics search query: %s", query)

            plain_result = None
            synced_result = None

            # 1. Try Genius first for high-quality plain text
            try:
                plain_result = syncedlyrics.search(
                    query,
                    plain_only=True,
                    providers=["Genius"],
                )
                if plain_result:
                    logger.debug("Found plain lyrics via Genius")
            except Exception as e:
                logger.debug("Genius plain search failed: %s", e)

            # 2. Try other plain providers
            if not plain_result:
                try:
                    plain_result = syncedlyrics.search(
                        query,
                        plain_only=True,
                        providers=[p for p in self.PLAIN_PROVIDERS if p != "Genius"],
                    )
                    if plain_result:
                        logger.debug("Found plain lyrics via fallback plain providers")
                except Exception as e:
                    logger.debug("Fallback plain search failed: %s", e)

            # 3. Try synced LRC providers
            try:
                synced_result = syncedlyrics.search(
                    query,
                    synced_only=True,
                    providers=self.SYNCED_PROVIDERS,
                )
                if synced_result:
                    logger.debug("Found synced lyrics")
            except Exception as e:
                logger.debug("Synced lyrics search failed: %s", e)

            if plain_result or synced_result:
                result = {
                    "id": None,
                    "name": query,
                    "trackName": None,
                    "artistName": None,
                    "albumName": None,
                    "duration": None,
                    "instrumental": False,
                    "plainLyrics": plain_result,
                    "syncedLyrics": synced_result,
                }
                logger.info(
                    "syncedlyrics found lyrics for: %s (plain=%s, synced=%s)",
                    query,
                    "yes" if plain_result else "no",
                    "yes" if synced_result else "no",
                )
                return [result]

            logger.info("No lyrics found via syncedlyrics for: %s", query)
            return []

        except Exception as e:
            logger.error("syncedlyrics search error: %s", e, exc_info=True)
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
