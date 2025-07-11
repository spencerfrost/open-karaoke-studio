"""
Time formatting utilities for LRC conversion.

This module provides functions for converting between different time formats
used in audio processing and LRC lyrics files.
"""


def seconds_to_lrc_format(seconds: float) -> str:
    """
    Convert decimal seconds to LRC timestamp format [mm:ss.xx].

    Args:
        seconds: Time in decimal seconds

    Returns:
        LRC format timestamp string

    Example:
        >>> seconds_to_lrc_format(93.45)
        '[01:33.45]'
    """
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"[{minutes:02d}:{remaining_seconds:05.2f}]"


def lrc_format_to_seconds(lrc_timestamp: str) -> float:
    """
    Convert LRC timestamp format [mm:ss.xx] to decimal seconds.

    Args:
        lrc_timestamp: LRC format timestamp string

    Returns:
        Time in decimal seconds

    Example:
        >>> lrc_format_to_seconds('[01:33.45]')
        93.45
    """
    # Remove brackets and split
    time_str = lrc_timestamp.strip("[]")
    minutes_str, seconds_str = time_str.split(":")

    minutes = int(minutes_str)
    seconds = float(seconds_str)

    return minutes * 60 + seconds


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string

    Example:
        >>> format_duration(183.5)
        '3:03.5'
    """
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:04.1f}"


def validate_timing_sequence(timestamps: list[float]) -> bool:
    """
    Validate that a sequence of timestamps is monotonically increasing.

    Args:
        timestamps: List of timestamps in seconds

    Returns:
        True if timestamps are in correct order, False otherwise
    """
    if len(timestamps) < 2:
        return True

    for i in range(1, len(timestamps)):
        if timestamps[i] < timestamps[i - 1]:
            return False

    return True
