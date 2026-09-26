"""
Data models for Whisper to LRC conversion.

This module contains the data classes and type definitions used throughout
the whisper-to-lrc conversion process.
"""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class LyricLine:
    """Represents a single line of lyrics with timing."""

    timestamp: float  # Start time in seconds
    text: str  # The lyric text
    confidence: float  # Average confidence of words in this line
    word_count: int  # Number of words in this line


@dataclass
class QualityMetrics:
    """Quality assessment metrics for generated lyrics."""

    avg_confidence: float
    low_confidence_words: int
    total_words: int
    coverage_percentage: float
    timing_consistency: float
    recommended_review: bool


@dataclass
class LyricsData:
    """Container for processed lyrics data."""

    lines: List[LyricLine]
    quality: QualityMetrics
    metadata: Dict[str, Any]


@dataclass
class ConverterConfig:
    """Configuration parameters for the WhisperToLRCConverter."""

    max_gap: float = 2.0  # Maximum gap in seconds to allow within a line
    min_words_per_line: int = 2  # Minimum words before forcing a line break
    max_words_per_line: int = 8  # Maximum words before forcing a line break
    target_words_per_line: int = 5  # Target number of words per line
    confidence_threshold: float = 0.3  # Minimum confidence score for words
