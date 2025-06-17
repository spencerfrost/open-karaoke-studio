# backend/app/services/metadata_service.py
"""
Service layer for music metadata operations.
This provides a clean abstraction for metadata search and formatting,
currently using iTunes as the backend but designed to be extensible.
"""

import json
from pathlib import Path
from typing import Any, Optional

from flask import current_app

from .interfaces.metadata_service import MetadataServiceInterface
from .itunes_service import (enhance_metadata_with_itunes,
                             get_itunes_cover_art, search_itunes)


def filter_youtube_metadata_for_storage(raw_data: dict[str, Any]) -> str:
    """
    Filter YouTube metadata for storage, removing massive formats array 
    and non-serializable objects.

    Args:
        raw_data: Raw YouTube metadata from yt-dlp

    Returns:
        JSON string of filtered metadata
    """

    def _make_serializable(obj):
        """Recursively make object JSON serializable"""
        if isinstance(obj, dict):
            return {k: _make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_make_serializable(item) for item in obj]
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        # Convert non-serializable objects to string representation
        return str(obj)

    filtered = raw_data.copy()

    # Remove the massive formats array (can be 50+ MB)
    if "formats" in filtered:
        del filtered["formats"]

    # Keep automatic_captions and subtitles for future features
    # Keep all other fields for completeness, but make them serializable

    try:
        # Try direct serialization first (fastest path)
        return json.dumps(filtered)
    except TypeError:
        # Fallback: clean non-serializable objects
        serializable_data = _make_serializable(filtered)
        return json.dumps(serializable_data)


def filter_itunes_metadata_for_storage(raw_data: dict[str, Any]) -> str:
    """Filter iTunes metadata for storage (minimal filtering needed)

    Args:
        raw_data: Raw iTunes response data

    Returns:
        JSON string of filtered metadata
    """
    # iTunes responses are compact, keep everything except wrapper
    if "resultCount" in raw_data:
        # Store just the first result, not the wrapper
        results = raw_data.get("results", [])
        return json.dumps(results[0] if results else {})

    return json.dumps(raw_data)


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
            current_app.logger.info(
                "MetadataService: Searching for artist='%s', title='%s', album='%s', limit=%s",
                artist,
                title,
                album,
                limit,
            )

            # Use iTunes service as the backend
            results = search_itunes(artist, title, album, limit)

            current_app.logger.info("MetadataService: Found %s results", len(results))
            return results

        except Exception as e:
            current_app.logger.error("MetadataService search error: %s", e)
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

    def enhance_song_metadata(self, metadata: dict[str, Any], song_dir: Path) -> dict[str, Any]:
        """
        Enhance existing song metadata with additional information.

        Args:
            metadata: Existing song metadata
            song_dir: Song directory for cover art download

        Returns:
            Dict[str, Any]: Enhanced metadata
        """
        try:
            current_app.logger.info(
                "MetadataService: Enhancing metadata for '%s' by '%s'",
                metadata.get("title", "Unknown"),
                metadata.get("artist", "Unknown"),
            )

            # Use iTunes service to enhance metadata
            enhanced = enhance_metadata_with_itunes(metadata, song_dir)

            current_app.logger.info("MetadataService: Metadata enhancement completed")
            return enhanced

        except Exception as e:
            current_app.logger.error("MetadataService enhancement error: %s", e)
            return metadata

    def download_cover_art(self, track_data: dict[str, Any], song_dir: Path) -> Optional[str]:
        """
        Download cover art for a track.

        Args:
            track_data: Track metadata containing artwork URLs
            song_dir: Directory to save cover art

        Returns:
            str: Relative path to downloaded cover art or None
        """
        try:
            current_app.logger.info(
                "MetadataService: Downloading cover art for track ID %s",
                track_data.get("id", "Unknown"),
            )

            # Use iTunes service to download cover art
            cover_path = get_itunes_cover_art(track_data, song_dir)

            if cover_path:
                current_app.logger.info("MetadataService: Cover art downloaded to %s", cover_path)
            else:
                current_app.logger.warning(
                    "MetadataService: No cover art available or download failed"
                )

            return cover_path

        except Exception as e:
            current_app.logger.error("MetadataService cover art download error: %s", e)
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
