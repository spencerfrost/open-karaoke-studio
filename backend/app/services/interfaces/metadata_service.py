# backend/app/services/interfaces/metadata_service.py
# pylint: disable=unnecessary-ellipsis
"""
Metadata Service Interface for dependency injection and testing
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MetadataServiceInterface(Protocol):
    """Interface for Metadata Service to enable dependency injection and testing"""

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
        ...

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
        ...
