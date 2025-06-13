#!/usr/bin/env python3
"""
Core conversion script: Faster Whisper JSON output to LRC format lyrics.

This module handles the conversion of Faster Whisper transcription output 
(with word-level timestamps) into LRC-format synced lyrics suitable for karaoke use.
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LyricLine:
    """Represents a single line of lyrics with timing."""
    timestamp: float  # Start time in seconds
    text: str        # The lyric text
    confidence: float # Average confidence of words in this line
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


class WhisperToLRCConverter:
    """
    Converts Faster Whisper JSON output to LRC format lyrics.
    
    Handles intelligent line breaking, quality assessment, and 
    timing format conversion for karaoke use.
    """
    
    def __init__(self, 
                 max_gap: float = 2.0,
                 min_words_per_line: int = 2,
                 max_words_per_line: int = 8,
                 target_words_per_line: int = 5,
                 confidence_threshold: float = 0.3):
        """
        Initialize the converter with configuration parameters.
        
        Args:
            max_gap: Maximum gap in seconds to allow within a line
            min_words_per_line: Minimum words before forcing a line break
            max_words_per_line: Maximum words before forcing a line break
            target_words_per_line: Target number of words per line
            confidence_threshold: Minimum confidence score for words
        """
        self.max_gap = max_gap
        self.min_words_per_line = min_words_per_line
        self.max_words_per_line = max_words_per_line
        self.target_words_per_line = target_words_per_line
        self.confidence_threshold = confidence_threshold

    def parse_whisper_output(self, json_data: Dict[str, Any]) -> LyricsData:
        """
        Parse Faster Whisper JSON output and convert to structured lyrics data.
        
        Args:
            json_data: The JSON output from Faster Whisper transcription
            
        Returns:
            LyricsData object with processed lyrics and quality metrics
        """
        # Extract words from the JSON data
        words = json_data.get('words', [])
        segments = json_data.get('segments', [])
        
        if not words:
            # Try to extract words from segments if not in root
            words = []
            for segment in segments:
                if 'words' in segment:
                    words.extend(segment['words'])
        
        # Filter out low-confidence words
        filtered_words = [
            word for word in words 
            if word.get('probability', 0) >= self.confidence_threshold
        ]
        
        # Group words into lines
        lyric_lines = self.group_words_into_lines(filtered_words)
        
        # Calculate quality metrics
        quality = self.assess_quality(words, segments)
        
        # Extract metadata
        metadata = {
            'audio_file': json_data.get('audio_file', ''),
            'detected_language': json_data.get('detected_language', ''),
            'language_probability': json_data.get('language_probability', 0),
            'duration': json_data.get('duration', 0),
            'processing_time': json_data.get('processing_time', 0),
            'original_word_count': len(words),
            'filtered_word_count': len(filtered_words)
        }
        
        return LyricsData(lines=lyric_lines, quality=quality, metadata=metadata)

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
                word, 
                words[i+1:] if i+1 < len(words) else [], 
                current_line_words
            )
            
            if should_break or i == len(words) - 1:  # Last word
                if current_line_words:
                    line = self._create_line_from_words(current_line_words)
                    lines.append(line)
                    current_line_words = []
        
        return lines

    def _should_break_line(self, 
                          current_word: Dict[str, Any], 
                          next_words: List[Dict[str, Any]], 
                          current_line: List[Dict[str, Any]]) -> bool:
        """
        Determine if a line break should occur after the current word.
        
        Args:
            current_word: The current word being processed
            next_words: Remaining words in the sequence
            current_line: Words already in the current line
            
        Returns:
            True if a line break should occur
        """
        word_text = current_word.get('word', '').strip()
        
        # Force break if line is getting too long
        if len(current_line) >= self.max_words_per_line:
            return True
        
        # Don't break if line is too short (unless we hit punctuation)
        if len(current_line) < self.min_words_per_line:
            # Only break for strong punctuation
            if word_text.endswith(('.', '!', '?')):
                return True
            return False
        
        # Break if there's a large gap to the next word (silence)
        if next_words:
            next_word = next_words[0]
            gap = next_word.get('start', 0) - current_word.get('end', 0)
            if gap > self.max_gap:
                return True
        
        # Break at sentence endings
        if word_text.endswith(('.', '!', '?')):
            return True
        
        # Break at comma if line is reasonably long
        if word_text.endswith(',') and len(current_line) >= self.target_words_per_line - 1:
            return True
        
        # Break if we're at target length and hit a natural boundary
        if len(current_line) >= self.target_words_per_line:
            # Look for natural breaking points
            if word_text.endswith((',', ';', ':')):
                return True
            # Break after common function words at target length
            if word_text.lower() in ['and', 'or', 'but', 'so', 'when', 'where', 'that']:
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
        timestamp = words[0].get('start', 0)
        
        # Combine word text with proper spacing
        text_parts = []
        for word in words:
            word_text = word.get('word', '').strip()
            if word_text:
                text_parts.append(word_text)
        
        text = ' '.join(text_parts)
        
        # Calculate average confidence
        confidences = [word.get('probability', 0) for word in words]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return LyricLine(
            timestamp=timestamp,
            text=text,
            confidence=avg_confidence,
            word_count=len(words)
        )

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
            timestamp_str = self._seconds_to_lrc_format(line.timestamp)
            lrc_lines.append(f"{timestamp_str} {line.text}")
        
        return '\n'.join(lrc_lines)

    def _seconds_to_lrc_format(self, seconds: float) -> str:
        """
        Convert decimal seconds to LRC timestamp format [mm:ss.xx].
        
        Args:
            seconds: Time in decimal seconds
            
        Returns:
            LRC format timestamp string
        """
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"[{minutes:02d}:{remaining_seconds:05.2f}]"

    def assess_quality(self, words: List[Dict[str, Any]], 
                      segments: List[Dict[str, Any]]) -> QualityMetrics:
        """
        Assess the quality of the transcription and provide metrics.
        
        Args:
            words: List of all words from transcription
            segments: List of segments from transcription
            
        Returns:
            QualityMetrics object with assessment data
        """
        if not words:
            return QualityMetrics(
                avg_confidence=0,
                low_confidence_words=0,
                total_words=0,
                coverage_percentage=0,
                timing_consistency=0,
                recommended_review=True
            )
        
        # Calculate confidence metrics
        confidences = [word.get('probability', 0) for word in words]
        avg_confidence = sum(confidences) / len(confidences)
        low_confidence_words = len([c for c in confidences if c < self.confidence_threshold])
        
        # Calculate coverage percentage (simplified)
        coverage_percentage = self._calculate_coverage(segments)
        
        # Check timing consistency
        timing_consistency = self._check_timing_consistency(words)
        
        # Determine if manual review is recommended
        recommended_review = (
            avg_confidence < 0.6 or
            low_confidence_words / len(words) > 0.3 or
            coverage_percentage < 0.8 or
            timing_consistency < 0.8
        )
        
        return QualityMetrics(
            avg_confidence=avg_confidence,
            low_confidence_words=low_confidence_words,
            total_words=len(words),
            coverage_percentage=coverage_percentage,
            timing_consistency=timing_consistency,
            recommended_review=recommended_review
        )

    def _calculate_coverage(self, segments: List[Dict[str, Any]]) -> float:
        """
        Calculate the percentage of time covered by transcribed segments.
        
        This is a simplified calculation that assumes segments represent
        the actual vocal content coverage.
        
        Args:
            segments: List of transcription segments
            
        Returns:
            Coverage percentage as a float between 0 and 1
        """
        if not segments:
            return 0.0
        
        # Calculate total duration of segments
        total_segment_duration = sum(
            segment.get('end', 0) - segment.get('start', 0)
            for segment in segments
        )
        
        # Estimate total audio duration (use the end of the last segment)
        if segments:
            total_duration = max(segment.get('end', 0) for segment in segments)
            if total_duration > 0:
                return min(1.0, total_segment_duration / total_duration)
        
        return 0.8  # Default assumption of reasonable coverage

    def _check_timing_consistency(self, words: List[Dict[str, Any]]) -> float:
        """
        Check for timing consistency and gaps in the transcription.
        
        Args:
            words: List of word dictionaries with timing
            
        Returns:
            Consistency score as a float between 0 and 1
        """
        if len(words) < 2:
            return 1.0
        
        # Check for reasonable gaps between words
        large_gaps = 0
        total_gaps = 0
        
        for i in range(len(words) - 1):
            current_end = words[i].get('end', 0)
            next_start = words[i + 1].get('start', 0)
            gap = next_start - current_end
            
            total_gaps += 1
            if gap > 5.0:  # Gap larger than 5 seconds is suspicious
                large_gaps += 1
        
        if total_gaps == 0:
            return 1.0
        
        # Return consistency score (fewer large gaps = higher consistency)
        return max(0.0, 1.0 - (large_gaps / total_gaps))


def convert_whisper_json_to_lrc(json_file_path: str, 
                               output_file_path: Optional[str] = None,
                               **converter_kwargs) -> Tuple[str, LyricsData]:
    """
    Convenience function to convert a Whisper JSON file to LRC format.
    
    Args:
        json_file_path: Path to the Faster Whisper JSON output file
        output_file_path: Optional path to save the LRC file (if None, not saved)
        **converter_kwargs: Additional arguments for WhisperToLRCConverter
        
    Returns:
        Tuple of (LRC string, LyricsData object)
    """
    # Load JSON data
    with open(json_file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # Convert to LRC
    converter = WhisperToLRCConverter(**converter_kwargs)
    lyrics_data = converter.parse_whisper_output(json_data)
    lrc_content = converter.convert_to_lrc(lyrics_data)
    
    # Save LRC file if output path provided
    if output_file_path:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(lrc_content)
        print(f"LRC file saved to: {output_file_path}")
    
    return lrc_content, lyrics_data


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python whisper_to_lrc.py <whisper_json_file> [output_lrc_file]")
        print("Example: python whisper_to_lrc.py vocals_whisper_results.json vocals.lrc")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not Path(json_file).exists():
        print(f"Error: JSON file not found: {json_file}")
        sys.exit(1)
    
    try:
        lrc_content, lyrics_data = convert_whisper_json_to_lrc(json_file, output_file)
        
        print("🎵 Conversion completed successfully!")
        print(f"📊 Generated {len(lyrics_data.lines)} lyric lines")
        print(f"⭐ Average confidence: {lyrics_data.quality.avg_confidence:.2f}")
        print(f"🔍 Review recommended: {'Yes' if lyrics_data.quality.recommended_review else 'No'}")
        
        if not output_file:
            print("\n📝 LRC Content:")
            print("-" * 40)
            print(lrc_content)
        
    except Exception as e:
        print(f"❌ Error converting file: {e}")
        sys.exit(1)
