# backend/app/services/lyrics_service.py
import logging
from typing import Any

import requests
from app.exceptions import ServiceError

logger = logging.getLogger(__name__)

USER_AGENT = (
    "OpenKaraokeStudio/0.1 (https://github.com/spencerfrost/open-karaoke-studio)"
)


class LyricsService:
    """Service for searching lyrics via LRCLIB with fallback support."""

    def __init__(self):
        self.primary_url = "https://lrclib.mrspinn.ca"
        self.backup_url = "https://lrclib.net"
        self.headers = {"User-Agent": USER_AGENT}

    def _make_request(self, path: str, params: dict) -> tuple[int, Any]:
        """
        Helper function to call LRCLIB API with fallback.
        Tries primary, then backup if primary fails.
        """
        urls = [self.primary_url, self.backup_url]
        last_exception = None
        for base_url in urls:
            url = f"{base_url}{path}"
            logger.debug("LRCLIB request: %s params=%s", url, params)
            try:
                resp = requests.get(url, params=params, headers=self.headers, timeout=10)
                status = resp.status_code
                try:
                    data = resp.json()
                except ValueError:
                    text = resp.text.strip()
                    if status >= 400:
                        data = {"error": text}
                    else:
                        data = {"error": "Invalid JSON from LRCLIB"}
                # Only treat as failure if network error or 5xx, not just 404/400
                if (status >= 500 or status == 0) and status not in {404, 400}:
                    raise ServiceError(f"LRCLIB server error: {status}")
                return status, data
            except requests.RequestException as e:
                logger.warning(f"Failed to make request to LRCLIB at {base_url}: {e}")
                last_exception = e
            except ServiceError as e:
                logger.warning(f"LRCLIB server error at {base_url}: {e}")
                last_exception = e
        logger.error("All LRCLIB endpoints failed: %s", last_exception)
        raise ServiceError(f"Failed to connect to any lyrics service: {last_exception}")

    def search_lyrics(self, query: str) -> list[dict[str, Any]]:
        """Search for lyrics using a general query string via LRCLIB."""
        try:
            search_params = {"q": query}
            status, results = self._make_request("/api/search", search_params)
            if status == 200 and isinstance(results, list):
                logger.info(
                    "Found %s lyrics results for query: %s", len(results), query
                )
                return results
            logger.info("No lyrics found for query: %s", query)
            return []
        except ServiceError:
            raise
        except Exception as e:
            logger.error("Unexpected error searching lyrics: %s", e)
            raise ServiceError(f"Failed to search lyrics: {e}")

    def search_lyrics_structured(self, params: dict[str, str]) -> list[dict[str, Any]]:
        """
        Search for lyrics using structured parameters
        (track_name, artist_name, album_name) via LRCLIB.
        """
        try:
            status, results = self._make_request("/api/search", params)
            if status == 200 and isinstance(results, list):
                logger.info(
                    "Found %s structured lyrics results for params: %s",
                    len(results),
                    params,
                )
                return results
            logger.info("No structured lyrics found for params: %s", params)
            return []
        except ServiceError:
            raise
        except Exception as e:
            logger.error("Unexpected error in structured lyrics search: %s", e)
            raise ServiceError(f"Failed to search lyrics with structured params: {e}")
