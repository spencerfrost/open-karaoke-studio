"""
Main entry point and convenience functions for Whisper to LRC conversion.

This module provides the main entry point and high-level convenience functions
for converting Faster Whisper JSON output to LRC format lyrics.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .converter import WhisperToLRCConverter, create_converter
from .models import ConverterConfig, LyricsData
from .quality import get_quality_summary


def convert_whisper_json_to_lrc(
    json_file_path: str, output_file_path: Optional[str] = None, **converter_kwargs
) -> Tuple[str, LyricsData]:
    """
    Convenience function to convert a Whisper JSON file to LRC format.

    This is the main high-level function that most users should use.

    Args:
        json_file_path: Path to the Faster Whisper JSON output file
        output_file_path: Optional path to save the LRC file (if None, not saved)
        **converter_kwargs: Additional arguments for WhisperToLRCConverter configuration

    Returns:
        Tuple of (LRC string, LyricsData object)

    Raises:
        FileNotFoundError: If the input JSON file doesn't exist
        json.JSONDecodeError: If the JSON file is malformed
        Exception: For other conversion errors

    Example:
        >>> lrc_content, lyrics_data = convert_whisper_json_to_lrc(
        ...     'vocals_whisper_results.json',
        ...     'vocals.lrc',
        ...     confidence_threshold=0.5,
        ...     max_gap=3.0
        ... )
        >>> print(f"Generated {len(lyrics_data.lines)} lyric lines")
    """
    # Validate input file
    json_path = Path(json_file_path)
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_file_path}")

    # Load JSON data
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON file: {e}", e.doc, e.pos)

    # Create converter and convert
    converter = create_converter(**converter_kwargs)
    lrc_content, lyrics_data = converter.convert_json_to_lrc(json_data)

    # Save LRC file if output path provided
    if output_file_path:
        output_path = Path(output_file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(lrc_content)

        print(f"✅ LRC file saved to: {output_file_path}")

    return lrc_content, lyrics_data


def convert_whisper_dict_to_lrc(
    json_data: Dict[str, Any], **converter_kwargs
) -> Tuple[str, LyricsData]:
    """
    Convert Whisper JSON data (as dictionary) to LRC format.

    Args:
        json_data: The JSON data from Faster Whisper transcription
        **converter_kwargs: Additional arguments for WhisperToLRCConverter configuration

    Returns:
        Tuple of (LRC string, LyricsData object)

    Example:
        >>> whisper_output = {"words": [...], "segments": [...]}
        >>> lrc_content, lyrics_data = convert_whisper_dict_to_lrc(whisper_output)
    """
    converter = create_converter(**converter_kwargs)
    return converter.convert_json_to_lrc(json_data)


def batch_convert_directory(
    input_dir: str, output_dir: str, pattern: str = "*.json", **converter_kwargs
) -> Dict[str, bool]:
    """
    Batch convert all JSON files in a directory to LRC format.

    Args:
        input_dir: Directory containing Whisper JSON files
        output_dir: Directory to save LRC files
        pattern: File pattern to match (default: "*.json")
        **converter_kwargs: Additional arguments for WhisperToLRCConverter configuration

    Returns:
        Dictionary mapping file names to success status

    Example:
        >>> results = batch_convert_directory(
        ...     '/path/to/whisper/outputs',
        ...     '/path/to/lrc/outputs',
        ...     confidence_threshold=0.4
        ... )
        >>> print(f"Successfully converted {sum(results.values())} files")
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Find all matching files
    json_files = list(input_path.glob(pattern))
    if not json_files:
        print(f"⚠️ No files matching pattern '{pattern}' found in {input_dir}")
        return {}

    results = {}
    converter = create_converter(**converter_kwargs)

    print(f"🔄 Processing {len(json_files)} files...")

    for json_file in json_files:
        try:
            # Load and convert
            with open(json_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            lrc_content, lyrics_data = converter.convert_json_to_lrc(json_data)

            # Save LRC file
            lrc_file = output_path / f"{json_file.stem}.lrc"
            with open(lrc_file, "w", encoding="utf-8") as f:
                f.write(lrc_content)

            print(
                f"✅ {json_file.name} -> {lrc_file.name} ({len(lyrics_data.lines)} lines)"
            )
            results[json_file.name] = True

        except Exception as e:
            print(f"❌ Failed to convert {json_file.name}: {e}")
            results[json_file.name] = False

    successful = sum(results.values())
    total = len(results)
    print(f"\n🎵 Batch conversion completed: {successful}/{total} files successful")

    return results


def validate_lrc_output(lrc_content: str) -> Dict[str, Any]:
    """
    Validate LRC output format and provide analysis.

    Args:
        lrc_content: LRC format string to validate

    Returns:
        Dictionary with validation results and statistics

    Example:
        >>> lrc = "[00:13.20] Baby on the way\\n[00:17.00] I was melting like ice"
        >>> validation = validate_lrc_output(lrc)
        >>> print(f"Valid: {validation['is_valid']}, Lines: {validation['line_count']}")
    """
    import re

    from .time_utils import lrc_format_to_seconds, validate_timing_sequence

    lines = lrc_content.strip().split("\n")
    valid_lines = []
    invalid_lines = []
    timestamps = []

    lrc_pattern = r"^\[(\d{2}:\d{2}\.\d{2})\]\s*(.*)$"

    for i, line in enumerate(lines):
        if not line.strip():
            continue

        match = re.match(lrc_pattern, line)
        if match:
            timestamp_str, text = match.groups()
            try:
                timestamp = lrc_format_to_seconds(f"[{timestamp_str}]")
                timestamps.append(timestamp)
                valid_lines.append((i + 1, timestamp, text))
            except:
                invalid_lines.append((i + 1, line, "Invalid timestamp format"))
        else:
            invalid_lines.append((i + 1, line, "Invalid LRC format"))

    # Check timestamp ordering
    timing_valid = validate_timing_sequence(timestamps)

    return {
        "is_valid": len(invalid_lines) == 0 and timing_valid,
        "line_count": len(lines),
        "valid_lines": len(valid_lines),
        "invalid_lines": len(invalid_lines),
        "timing_sequential": timing_valid,
        "duration": max(timestamps) - min(timestamps) if timestamps else 0,
        "avg_line_gap": (
            (max(timestamps) - min(timestamps)) / len(timestamps)
            if len(timestamps) > 1
            else 0
        ),
        "validation_errors": invalid_lines,
    }


# Re-export key classes and functions for convenience
__all__ = [
    "convert_whisper_json_to_lrc",
    "convert_whisper_dict_to_lrc",
    "batch_convert_directory",
    "validate_lrc_output",
    "WhisperToLRCConverter",
    "ConverterConfig",
    "LyricsData",
    "create_converter",
]

# Import for re-export
from .converter import WhisperToLRCConverter
from .models import ConverterConfig, LyricsData
