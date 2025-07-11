"""
Main converter class for Whisper to LRC conversion.

This module contains the primary WhisperToLRCConverter class that orchestrates
the conversion process using the other utility modules.
"""

import json
from typing import Any, Dict

from .line_breaker import LineBreaker
from .models import ConverterConfig, LyricsData
from .quality import assess_transcription_quality
from .time_utils import seconds_to_lrc_format


class WhisperToLRCConverter:
    """
    Converts Faster Whisper JSON output to LRC format lyrics.

    Handles intelligent line breaking, quality assessment, and
    timing format conversion for karaoke use.
    """

    def __init__(self, config: ConverterConfig = None):
        """
        Initialize the converter with configuration parameters.

        Args:
            config: ConverterConfig object with conversion parameters
        """
        self.config = config or ConverterConfig()
        self.line_breaker = LineBreaker(self.config)

    def parse_whisper_output(self, json_data: Dict[str, Any]) -> LyricsData:
        """
        Parse Faster Whisper JSON output and convert to structured lyrics data.

        Args:
            json_data: The JSON output from Faster Whisper transcription

        Returns:
            LyricsData object with processed lyrics and quality metrics
        """
        # Extract words from the JSON data
        words = self._extract_words(json_data)
        segments = json_data.get("segments", [])

        # Filter out low-confidence words
        filtered_words = self._filter_low_confidence_words(words)

        # Group words into lines
        lyric_lines = self.line_breaker.group_words_into_lines(filtered_words)

        # Calculate quality metrics
        quality = assess_transcription_quality(
            words, segments, self.config.confidence_threshold
        )

        # Extract metadata
        metadata = self._extract_metadata(json_data, words, filtered_words)

        return LyricsData(lines=lyric_lines, quality=quality, metadata=metadata)

    def convert_to_lrc(self, lyrics_data: LyricsData) -> str:
        """
        Convert lyrics data to standard LRC format.

        Args:
            lyrics_data: Processed lyrics data

        Returns:
            LRC format string
        """
        lrc_lines = []

        for line in lyrics_data.lines:
            timestamp_str = seconds_to_lrc_format(line.timestamp)
            lrc_lines.append(f"{timestamp_str} {line.text}")

        return "\n".join(lrc_lines)

    def convert_json_to_lrc(self, json_data: Dict[str, Any]) -> tuple[str, LyricsData]:
        """
        One-step conversion from Whisper JSON to LRC format.

        Args:
            json_data: The JSON output from Faster Whisper transcription

        Returns:
            Tuple of (LRC string, LyricsData object)
        """
        lyrics_data = self.parse_whisper_output(json_data)
        lrc_content = self.convert_to_lrc(lyrics_data)
        return lrc_content, lyrics_data

    def _extract_words(self, json_data: Dict[str, Any]) -> list[Dict[str, Any]]:
        """Extract words from Whisper JSON output."""
        words = json_data.get("words", [])

        if not words:
            # Try to extract words from segments if not in root
            segments = json_data.get("segments", [])
            words = []
            for segment in segments:
                if "words" in segment:
                    words.extend(segment["words"])

        return words

    def _filter_low_confidence_words(
        self, words: list[Dict[str, Any]]
    ) -> list[Dict[str, Any]]:
        """Filter out words below confidence threshold."""
        return [
            word
            for word in words
            if word.get("probability", 0) >= self.config.confidence_threshold
        ]

    def _extract_metadata(
        self,
        json_data: Dict[str, Any],
        original_words: list[Dict[str, Any]],
        filtered_words: list[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Extract metadata from the conversion process."""
        return {
            "audio_file": json_data.get("audio_file", ""),
            "detected_language": json_data.get("detected_language", ""),
            "language_probability": json_data.get("language_probability", 0),
            "duration": json_data.get("duration", 0),
            "processing_time": json_data.get("processing_time", 0),
            "original_word_count": len(original_words),
            "filtered_word_count": len(filtered_words),
            "confidence_threshold": self.config.confidence_threshold,
            "converter_config": {
                "max_gap": self.config.max_gap,
                "min_words_per_line": self.config.min_words_per_line,
                "max_words_per_line": self.config.max_words_per_line,
                "target_words_per_line": self.config.target_words_per_line,
            },
        }


def create_converter(
    max_gap: float = 2.0,
    min_words_per_line: int = 2,
    max_words_per_line: int = 8,
    target_words_per_line: int = 5,
    confidence_threshold: float = 0.3,
) -> WhisperToLRCConverter:
    """
    Factory function to create a configured converter.

    Args:
        max_gap: Maximum gap in seconds to allow within a line
        min_words_per_line: Minimum words before forcing a line break
        max_words_per_line: Maximum words before forcing a line break
        target_words_per_line: Target number of words per line
        confidence_threshold: Minimum confidence score for words

    Returns:
        Configured WhisperToLRCConverter instance
    """
    config = ConverterConfig(
        max_gap=max_gap,
        min_words_per_line=min_words_per_line,
        max_words_per_line=max_words_per_line,
        target_words_per_line=target_words_per_line,
        confidence_threshold=confidence_threshold,
    )
    return WhisperToLRCConverter(config)
