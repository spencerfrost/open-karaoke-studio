# backend/app/services/metadata_service.py
"""
Service layer for music metadata operations.
This provides a clean abstraction for metadata search and formatting,
currently using iTunes as the backend but designed to be extensible.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from flask import current_app

logger = logging.getLogger(__name__)

from ..utils.metadata import (
    filter_itunes_metadata_for_storage,
    filter_youtube_metadata_for_storage,
)
from .interfaces.metadata_service import MetadataServiceInterface
from .itunes_service import (
    enhance_metadata_with_itunes,
    get_itunes_cover_art,
    search_itunes,
)


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
                "MetadataService: Searching for artist='%s', title='%s', album='%s', limit=%s",
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
        # Map iTunes results to a consistent metadata format
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
                "duration": result.get("durationSeconds"),
                "trackNumber": result.get("trackNumber"),
                "previewUrl": result.get("previewUrl", ""),
                "explicit": result.get("trackExplicitness") != "notExplicit",
                # Artwork URLs in a structured format
                "artworkUrls": {
                    "small": result.get("artworkUrl30", ""),
                    "medium": result.get("artworkUrl60", ""),
                    "large": result.get("artworkUrl100", ""),
                },
                # Legacy field for backwards compatibility
                "artworkUrl": result.get("artworkUrl100", ""),
                "isStreamable": result.get("isStreamable", False),
                # Additional iTunes-specific fields that might be useful
                "artistId": result.get("artistId"),
                "albumId": result.get("albumId"),
                "discNumber": result.get("discNumber"),
                "country": result.get("country", ""),
                "price": result.get("price"),
                # Include the raw iTunes data for frontend compatibility
                "rawData": result,
            }

            metadata_results.append(metadata_result)

        return {
            "results": metadata_results,
            "searchParams": search_params,
            "count": len(metadata_results),
            "success": True,
        }

    def enhance_song_metadata(
        self, metadata: dict[str, Any], song_dir: Path
    ) -> dict[str, Any]:
        """
        Enhance existing song metadata with additional information.

        Args:
            metadata: Existing song metadata
            song_dir: Song directory for cover art download

        Returns:
            Dict[str, Any]: Enhanced metadata
        """
        try:
            logger.info(
                "MetadataService: Enhancing metadata for '%s' by '%s'",
                metadata.get("title", "Unknown"),
                metadata.get("artist", "Unknown"),
            )

            # Use iTunes service to enhance metadata
            enhanced = enhance_metadata_with_itunes(metadata, song_dir)

            logger.info("MetadataService: Metadata enhancement completed")
            return enhanced

        except Exception as e:
            logger.error("MetadataService enhancement error: %s", e)
            return metadata

    def download_cover_art(
        self, track_data: dict[str, Any], song_dir: Path
    ) -> Optional[str]:
        """
        Download cover art for a track.

        Args:
            track_data: Track metadata containing artwork URLs
            song_dir: Directory to save cover art

        Returns:
            str: Relative path to downloaded cover art or None
        """
        try:
            logger.info(
                "MetadataService: Downloading cover art for track ID %s",
                track_data.get("id", "Unknown"),
            )

            # Use iTunes service to download cover art
            cover_path = get_itunes_cover_art(track_data, song_dir)

            if cover_path:
                logger.info("MetadataService: Cover art downloaded to %s", cover_path)
            else:
                logger.warning(
                    "MetadataService: No cover art available or download failed"
                )

            return cover_path

        except Exception as e:
            logger.error("MetadataService cover art download error: %s", e)
            return None


# Convenience function for backwards compatibility and direct usage
def search_metadata(
    artist: str, title: str, album: str = "", limit: int = 5
) -> list[dict[str, Any]]:
    """
    Convenience function for metadata search.

    Args:
        artist (str): Artist name
        title (str): Song title
        album (str): Album name (optional)
        limit (int): Maximum number of results to return

    Returns:
        List[Dict[str, Any]]: List of song metadata
    """
    service = MetadataService()
    return service.search_metadata(artist, title, album, limit)
