"""
Line breaking algorithms for lyrics generation.

This module contains the logic for intelligently grouping words into
lyric lines suitable for karaoke display.
"""

from typing import Any, Dict, List

from .models import ConverterConfig, LyricLine


class LineBreaker:
    """Handles intelligent line breaking for lyrics."""

    def __init__(self, config: ConverterConfig):
        """
        Initialize with converter configuration.

        Args:
            config: ConverterConfig object with line breaking parameters
        """
        self.config = config

    def group_words_into_lines(self, words: List[Dict[str, Any]]) -> List[LyricLine]:
        """
        Group words into appropriate lyric lines for karaoke display.

        Uses intelligent breaking based on timing gaps, punctuation,
        and target line length.

        Args:
            words: List of word dictionaries with timing and text

        Returns:
            List of LyricLine objects
        """
        if not words:
            return []

        lines = []
        current_line_words = []

        for i, word in enumerate(words):
            current_line_words.append(word)

            # Check if we should break the line
            should_break = self._should_break_line(
                word, words[i + 1 :] if i + 1 < len(words) else [], current_line_words
            )

            if should_break or i == len(words) - 1:  # Last word
                if current_line_words:
                    line = self._create_line_from_words(current_line_words)
                    lines.append(line)
                    current_line_words = []

        return lines

    def _should_break_line(
        self,
        current_word: Dict[str, Any],
        next_words: List[Dict[str, Any]],
        current_line: List[Dict[str, Any]],
    ) -> bool:
        """
        Determine if a line break should occur after the current word.

        Args:
            current_word: The current word being processed
            next_words: Remaining words in the sequence
            current_line: Words already in the current line

        Returns:
            True if a line break should occur
        """
        word_text = current_word.get("word", "").strip()

        # Force break if line is getting too long
        if len(current_line) >= self.config.max_words_per_line:
            return True

        # Don't break if line is too short (unless we hit punctuation)
        if len(current_line) < self.config.min_words_per_line:
            # Only break for strong punctuation
            if word_text.endswith((".", "!", "?")):
                return True
            return False

        # Break if there's a large gap to the next word (silence)
        if next_words:
            next_word = next_words[0]
            gap = next_word.get("start", 0) - current_word.get("end", 0)
            if gap > self.config.max_gap:
                return True

        # Break at sentence endings
        if word_text.endswith((".", "!", "?")):
            return True

        # Break at comma if line is reasonably long
        if (
            word_text.endswith(",")
            and len(current_line) >= self.config.target_words_per_line - 1
        ):
            return True

        # Break if we're at target length and hit a natural boundary
        if len(current_line) >= self.config.target_words_per_line:
            # Look for natural breaking points
            if word_text.endswith((",", ";", ":")):
                return True
            # Break after common function words at target length
            if word_text.lower() in ["and", "or", "but", "so", "when", "where", "that"]:
                return True

        return False

    def _create_line_from_words(self, words: List[Dict[str, Any]]) -> LyricLine:
        """
        Create a LyricLine object from a list of words.

        Args:
            words: List of word dictionaries

        Returns:
            LyricLine object with combined text and metadata
        """
        if not words:
            return LyricLine(timestamp=0, text="", confidence=0, word_count=0)

        # Use the start time of the first word
        timestamp = words[0].get("start", 0)

        # Combine word text with proper spacing
        text_parts = []
        for word in words:
            word_text = word.get("word", "").strip()
            if word_text:
                text_parts.append(word_text)

        text = " ".join(text_parts)

        # Calculate average confidence
        confidences = [word.get("probability", 0) for word in words]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return LyricLine(
            timestamp=timestamp,
            text=text,
            confidence=avg_confidence,
            word_count=len(words),
        )


def detect_natural_breaks(
    words: List[Dict[str, Any]], max_silence_gap: float = 1.5
) -> List[int]:
    """
    Detect natural break points in speech based on silence gaps.

    Args:
        words: List of word dictionaries with timing
        max_silence_gap: Maximum gap to consider as natural speech pause

    Returns:
        List of word indices where natural breaks occur
    """
    breaks = []

    for i in range(len(words) - 1):
        current_end = words[i].get("end", 0)
        next_start = words[i + 1].get("start", 0)
        gap = next_start - current_end

        if gap > max_silence_gap:
            breaks.append(i)

    return breaks


def is_sentence_boundary(word_text: str) -> bool:
    """
    Check if a word represents a sentence boundary.

    Args:
        word_text: The word text to check

    Returns:
        True if this word ends a sentence
    """
    return word_text.strip().endswith((".", "!", "?"))


def is_phrase_boundary(word_text: str) -> bool:
    """
    Check if a word represents a phrase boundary.

    Args:
        word_text: The word text to check

    Returns:
        True if this word ends a phrase
    """
    return word_text.strip().endswith((",", ";", ":"))
