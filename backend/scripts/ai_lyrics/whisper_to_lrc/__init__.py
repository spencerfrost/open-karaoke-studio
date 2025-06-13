"""
Whisper to LRC Conversion Package

A modular package for converting Faster Whisper transcription output
to LRC format lyrics suitable for karaoke applications.

Main Functions:
    convert_whisper_json_to_lrc: Convert JSON file to LRC format
    convert_whisper_dict_to_lrc: Convert JSON data to LRC format
    batch_convert_directory: Batch convert multiple files
    
Classes:
    WhisperToLRCConverter: Main conversion class
    ConverterConfig: Configuration for conversion parameters
    LyricsData: Container for processed lyrics and quality data
    
Example Usage:
    >>> from whisper_to_lrc import convert_whisper_json_to_lrc
    >>> lrc_content, lyrics_data = convert_whisper_json_to_lrc(
    ...     'vocals_whisper_results.json',
    ...     'vocals.lrc',
    ...     confidence_threshold=0.5
    ... )
    >>> print(f"Generated {len(lyrics_data.lines)} lyric lines")
"""

from .main import (
    convert_whisper_json_to_lrc,
    convert_whisper_dict_to_lrc,
    batch_convert_directory,
    validate_lrc_output
)

from .converter import WhisperToLRCConverter, create_converter
from .models import ConverterConfig, LyricsData, LyricLine, QualityMetrics
from .quality import assess_transcription_quality, get_quality_summary
from .time_utils import seconds_to_lrc_format, lrc_format_to_seconds
from .line_breaker import LineBreaker

# Package metadata
__version__ = "1.0.0"
__author__ = "Open Karaoke Studio"
__description__ = "Convert Faster Whisper transcription to LRC format lyrics"

# Main exports for easy access
__all__ = [
    # Main functions
    'convert_whisper_json_to_lrc',
    'convert_whisper_dict_to_lrc',
    'batch_convert_directory',
    'validate_lrc_output',
    
    # Core classes
    'WhisperToLRCConverter',
    'ConverterConfig',
    'LyricsData',
    'LyricLine',
    'QualityMetrics',
    'LineBreaker',
    
    # Utility functions
    'create_converter',
    'assess_transcription_quality',
    'get_quality_summary',
    'seconds_to_lrc_format',
    'lrc_format_to_seconds',
    
    # Package info
    '__version__',
    '__author__',
    '__description__'
]
