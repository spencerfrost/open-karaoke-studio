# backend/app/services/metadata_service.py
"""
Service layer for music metadata operations.
This provides a clean abstraction for metadata search and formatting,
currently using iTunes as the backend but designed to be extensible.
"""

import logging
from typing import Any

from .interfaces.metadata_service import MetadataServiceInterface
from .itunes_service import search_itunes

logger = logging.getLogger(__name__)


class MetadataService(MetadataServiceInterface):
    """Service for music metadata operations using iTunes as the backend."""

    def search_metadata(
        self, artist: str, title: str, album: str = "", limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Search for song metadata.

        Args:
            artist (str): Artist name
            title (str): Song title
            album (str): Album name (optional)
            limit (int): Maximum number of results to return

        Returns:
            List[Dict[str, Any]]: List of song metadata
        """
        try:
            logger.info(
                (
                    "MetadataService: Searching for artist='%s', title='%s', "
                    "album='%s', limit=%s"
                ),
                artist,
                title,
                album,
                limit,
            )

            # Use iTunes service as the backend
            results = search_itunes(artist, title, album, limit)

            logger.info("MetadataService: Found %s results", len(results))
            return results

        except Exception as e:
            logger.error("MetadataService search error: %s", e)
            raise

    def format_metadata_response(
        self, results: list[dict[str, Any]], search_params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Format metadata search results into a consistent API response.

        Args:
            results: List of metadata results
            search_params: Original search parameters

        Returns:
            Dict[str, Any]: Formatted response data
        """
        metadata_results = []

        for result in results:
            metadata_result = {
                "metadataId": str(result.get("id", "")),
                "title": result.get("title", ""),
                "artist": result.get("artist", ""),
                "album": result.get("album", ""),
                "releaseDate": result.get("releaseDateFormatted", ""),
                "releaseYear": result.get("releaseYear"),
                "genre": result.get("genre", ""),
                "trackNumber": result.get("trackNumber"),
                "previewUrl": result.get("previewUrl", ""),
                "explicit": result.get("trackExplicitness") != "notExplicit",
                "isStreamable": result.get("isStreamable", False),
                "artistId": result.get("artistId"),
                "albumId": result.get("albumId"),
                "discNumber": result.get("discNumber"),
                "country": result.get("country", ""),
                "price": result.get("price"),
                "rawData": result,
            }

            metadata_results.append(metadata_result)

        return {
            "results": metadata_results,
            "searchParams": search_params,
            "count": len(metadata_results),
            "success": True,
        }
