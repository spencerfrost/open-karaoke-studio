# backend/app/utils/metadata.py
"""
Metadata filtering utilities.

Shared utilities for filtering and processing metadata from various sources.
This module prevents cyclic imports between service modules.
"""

import json
from typing import Any, Dict


def filter_youtube_metadata_for_storage(raw_data: Dict[str, Any]) -> str:
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


def filter_itunes_metadata_for_storage(raw_data: Dict[str, Any]) -> str:
    """
    Filter iTunes metadata for storage (minimal filtering needed).

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
