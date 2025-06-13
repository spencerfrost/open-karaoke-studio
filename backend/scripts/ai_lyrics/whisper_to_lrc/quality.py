"""
Quality assessment utilities for transcription analysis.

This module provides functions to assess the quality of Faster Whisper
transcription output and determine if manual review is recommended.
"""

from typing import List, Dict, Any
from .models import QualityMetrics


def assess_transcription_quality(words: List[Dict[str, Any]],
                                segments: List[Dict[str, Any]],
                                confidence_threshold: float = 0.3) -> QualityMetrics:
    """
    Assess the quality of the transcription and provide metrics.
    
    Args:
        words: List of all words from transcription
        segments: List of segments from transcription
        confidence_threshold: Minimum confidence threshold for quality assessment

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
    low_confidence_words = len([c for c in confidences if c < confidence_threshold])

    # Calculate coverage percentage
    coverage_percentage = calculate_coverage(segments)

    # Check timing consistency
    timing_consistency = check_timing_consistency(words)

    # Determine if manual review is recommended
    recommended_review = should_recommend_review(
        avg_confidence,
        low_confidence_words,
        len(words),
        coverage_percentage,
        timing_consistency
    )

    return QualityMetrics(
        avg_confidence=avg_confidence,
        low_confidence_words=low_confidence_words,
        total_words=len(words),
        coverage_percentage=coverage_percentage,
        timing_consistency=timing_consistency,
        recommended_review=recommended_review
    )


def calculate_coverage(segments: List[Dict[str, Any]]) -> float:
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


def check_timing_consistency(words: List[Dict[str, Any]]) -> float:
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


def should_recommend_review(avg_confidence: float,
                           low_confidence_words: int,
                           total_words: int,
                           coverage_percentage: float,
                           timing_consistency: float) -> bool:
    """
    Determine if manual review should be recommended based on quality metrics.
    
    Args:
        avg_confidence: Average confidence score
        low_confidence_words: Number of low confidence words
        total_words: Total number of words
        coverage_percentage: Coverage percentage
        timing_consistency: Timing consistency score
        
    Returns:
        True if manual review is recommended
    """
    # Review recommended if any of these conditions are met
    if avg_confidence < 0.6:
        return True
    
    if total_words > 0 and (low_confidence_words / total_words) > 0.3:
        return True
    
    if coverage_percentage < 0.8:
        return True
    
    if timing_consistency < 0.8:
        return True

    return False


def get_quality_summary(quality: QualityMetrics) -> str:
    """
    Generate a human-readable summary of transcription quality.
    
    Args:
        quality: QualityMetrics object

    Returns:
        Summary string describing the quality
    """
    if quality.total_words == 0:
        return "❌ No words detected in transcription"
    
    confidence_level = "excellent" if quality.avg_confidence > 0.8 else \
                      "good" if quality.avg_confidence > 0.6 else \
                      "fair" if quality.avg_confidence > 0.4 else "poor"
    
    summary_parts = [
        f"📊 {quality.total_words} words detected",
        f"⭐ {confidence_level} confidence ({quality.avg_confidence:.2f})",
        f"📈 {quality.coverage_percentage:.1%} coverage",
        f"⏱️  timing consistency: {quality.timing_consistency:.2f}"
    ]
    
    if quality.recommended_review:
        summary_parts.append("🔍 Manual review recommended")
    else:
        summary_parts.append("✅ Quality acceptable")

    return " | ".join(summary_parts)
