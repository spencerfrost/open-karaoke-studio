"""
Global LRC timestamp offset detection and correction.

Detects whether a song's synced LRC timestamps are globally shifted relative to
the actual audio by comparing LRC line timestamps against detected vocal onsets
in the vocals track.  Returns an estimated offset (seconds) that can be applied
to all timestamps to re-align the lyrics with the audio.

Usage pattern:
    result = analyze_global_offset(lrc_content, vocals_path)
    if result["confidence"] in ("high", "medium"):
        corrected = shift_lrc_timestamps(lrc_content, -result["estimated_offset"])
"""

import logging
import re
from pathlib import Path
from statistics import median
from typing import Literal, Optional

import numpy as np

from .audio import compute_rms_curve, load_vocals
from .lyrics_analysis import (
    LrcLine,
    SectionBreakCandidate,
    analyze_timing_gaps,
    fuse_candidates,
    parse_lrc_lines,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TypedDicts
# ---------------------------------------------------------------------------

from typing import TypedDict


class AnchorMeasurement(TypedDict):
    lrc_timestamp: float
    detected_onset: Optional[float]
    offset: Optional[float]
    line_text: str
    anchor_type: str  # "first_line" | "section_boundary"
    excluded: bool  # True if rejected as an outlier after measurement


class OffsetAnalysisResult(TypedDict):
    estimated_offset: Optional[float]
    confidence: Literal["high", "medium", "low", "insufficient"]
    anchor_count: int
    successful_anchors: int
    anchors: list[AnchorMeasurement]
    max_deviation: Optional[float]


# ---------------------------------------------------------------------------
# LRC timestamp regex (matches [MM:SS.cs] and [MM:SS.mmm])
# ---------------------------------------------------------------------------

_LRC_TS_PATTERN = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{2,3}))?\]")

# Matches lines that look like LRC metadata rather than real lyrics.
# Patterns: "key : value", "key：value", or lines dominated by CJK with a colon.
# Examples: "作词 : Someone", "词：Someone", "Produced by:"
_METADATA_LINE_RE = re.compile(
    r"^[\w\s\u4e00-\u9fff\u3040-\u30ff\uAC00-\uD7A3]{1,20}\s*[：:]\s*\S",
    re.UNICODE,
)


def _is_metadata_line(text: str) -> bool:
    """Return True if the line looks like embedded metadata, not a lyric."""
    stripped = text.strip()
    if not stripped:
        return False
    return bool(_METADATA_LINE_RE.match(stripped))


def _ts_to_seconds(minutes: int, seconds: int, frac_str: Optional[str]) -> float:
    frac_str = frac_str or "0"
    if len(frac_str) == 3:
        frac = int(frac_str) / 1000.0
    else:
        frac = int(frac_str) / 100.0
    return minutes * 60.0 + seconds + frac


def _seconds_to_lrc_ts(ts: float) -> str:
    """Convert a float timestamp to [MM:SS.cs] format."""
    if ts < 0:
        ts = 0.0
    minutes = int(ts // 60)
    seconds = ts % 60
    return f"[{minutes:02d}:{seconds:05.2f}]"


# ---------------------------------------------------------------------------
# Vocal onset detection
# ---------------------------------------------------------------------------

# Silence floor: frames below this RMS value count as "silent"
_SILENCE_THRESHOLD_DEFAULT = 0.01
# Onset threshold: first frame above this RMS value (after silence) is the onset
_ONSET_THRESHOLD_DEFAULT = 0.02


def _detect_vocal_onset(
    rms: np.ndarray,
    rms_times: np.ndarray,
    search_start_s: float,
    search_end_s: float,
    silence_threshold: float = _SILENCE_THRESHOLD_DEFAULT,
    onset_threshold: float = _ONSET_THRESHOLD_DEFAULT,
) -> Optional[float]:
    """Detect the first vocal onset within a time window.

    Scans through the RMS curve looking for a frame that follows a silent region
    and rises above onset_threshold.  Returns the time (seconds) of that frame,
    or None if no clear onset is found in the window.

    Args:
        rms: Per-frame RMS energy array.
        rms_times: Centre time in seconds for each RMS frame.
        search_start_s: Start of the search window (seconds).
        search_end_s: End of the search window (seconds).
        silence_threshold: RMS level considered silent.
        onset_threshold: RMS level that defines the onset edge.

    Returns:
        Onset time in seconds, or None.
    """
    # Clamp window to valid range
    search_start_s = max(0.0, search_start_s)
    search_end_s = min(float(rms_times[-1]), search_end_s)

    # Slice to the window
    mask = (rms_times >= search_start_s) & (rms_times <= search_end_s)
    window_rms = rms[mask]
    window_times = rms_times[mask]

    if len(window_rms) < 2:
        return None

    # Look for first frame above onset_threshold that was preceded by silence
    was_silent = window_rms[0] < silence_threshold
    for i in range(1, len(window_rms)):
        if was_silent and window_rms[i] >= onset_threshold:
            return float(window_times[i])
        if window_rms[i] < silence_threshold:
            was_silent = True
        # Once we're in loud territory, keep scanning for a silence→onset edge

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_global_offset(
    lrc_content: str,
    vocals_path: Path,
    min_anchor_confidence: float = 0.5,
    search_before_s: float = 3.0,
    search_after_s: float = 2.0,
    silence_threshold: float = _SILENCE_THRESHOLD_DEFAULT,
    onset_threshold: float = _ONSET_THRESHOLD_DEFAULT,
) -> OffsetAnalysisResult:
    """Estimate the global LRC timestamp offset by comparing timestamps to audio.

    Uses the first lyric line (always) plus lines immediately after high-confidence
    timing-gap section boundaries as measurement anchors.  For each anchor it
    searches for the nearest vocal onset in the audio, then takes the median of
    all measured offset values as the global estimate.

    Args:
        lrc_content: Raw LRC file content.
        vocals_path: Path to the vocals audio file (mp3/wav after Demucs).
        min_anchor_confidence: Minimum section-break confidence to use as anchor.
        search_before_s: How many seconds before the LRC timestamp to start searching.
        search_after_s: How many seconds after the LRC timestamp to stop searching.
        silence_threshold: RMS level considered silent for onset detection.
        onset_threshold: RMS level that defines the onset edge.

    Returns:
        OffsetAnalysisResult with estimated_offset, confidence, and per-anchor data.
    """
    lines = parse_lrc_lines(lrc_content)
    text_lines = [l for l in lines if l["text"]]

    if not text_lines:
        logger.warning("No text lines found in LRC content")
        return OffsetAnalysisResult(
            estimated_offset=None,
            confidence="insufficient",
            anchor_count=0,
            successful_anchors=0,
            anchors=[],
            max_deviation=None,
        )

    # --- Build anchor list ----------------------------------------------------
    # Anchor 1: the very first lyric line — skip if it looks like embedded metadata
    # (e.g. "作词 : Someone" found in some Chinese/Japanese LRC files)
    anchors: list[tuple[LrcLine, str]] = []
    first_line = text_lines[0]
    if _is_metadata_line(first_line["text"]):
        logger.debug(
            "Skipping first_line anchor '%s' — looks like metadata",
            first_line["text"][:60],
        )
    else:
        anchors.append((first_line, "first_line"))

    # Additional anchors: lines that immediately follow a high-confidence timing gap
    # (i.e. the line that starts a new section — fresh silence → onset pattern)
    timing_candidates = analyze_timing_gaps(lines)
    high_conf = [c for c in timing_candidates if c["confidence"] >= min_anchor_confidence]
    fused = fuse_candidates(high_conf) if high_conf else []

    # Map after_line_index → the LrcLine that comes right after the break
    line_by_index: dict[int, LrcLine] = {l["line_index"]: l for l in text_lines}
    for candidate in fused:
        # We want the line that starts the new section — that is the next text line
        # after the gap, not the last line before the gap.
        gap_after_idx = candidate["after_line_index"]
        # Find the first text line whose line_index > gap_after_idx
        next_text = next(
            (l for l in text_lines if l["line_index"] > gap_after_idx), None
        )
        if next_text and next_text not in [a for a, _ in anchors]:
            anchors.append((next_text, "section_boundary"))

    logger.info(
        "Offset analysis: %d anchor(s) selected (%d section boundaries)",
        len(anchors),
        len(anchors) - 1,
    )

    # --- Load audio once ------------------------------------------------------
    try:
        y, sr = load_vocals(vocals_path)
    except Exception as e:
        logger.error("Failed to load vocals from %s: %s", vocals_path, e, exc_info=True)
        return OffsetAnalysisResult(
            estimated_offset=None,
            confidence="insufficient",
            anchor_count=len(anchors),
            successful_anchors=0,
            anchors=[
                AnchorMeasurement(
                    lrc_timestamp=line["timestamp"],
                    detected_onset=None,
                    offset=None,
                    line_text=line["text"],
                    anchor_type=atype,
                    excluded=False,
                )
                for line, atype in anchors
            ],
            max_deviation=None,
        )

    rms, rms_times = compute_rms_curve(y, sr)

    # --- Measure offset per anchor --------------------------------------------
    measurements: list[AnchorMeasurement] = []
    offsets: list[float] = []

    for line, anchor_type in anchors:
        lrc_ts = line["timestamp"]
        onset = _detect_vocal_onset(
            rms,
            rms_times,
            search_start_s=lrc_ts - search_before_s,
            search_end_s=lrc_ts + search_after_s,
            silence_threshold=silence_threshold,
            onset_threshold=onset_threshold,
        )

        offset_val: Optional[float] = None
        if onset is not None:
            offset_val = round(lrc_ts - onset, 3)
            offsets.append(offset_val)
            logger.debug(
                "Anchor '%s' @ %.2fs: onset=%.2fs  offset=%.3fs",
                line["text"][:40],
                lrc_ts,
                onset,
                offset_val,
            )
        else:
            logger.debug(
                "Anchor '%s' @ %.2fs: no onset detected in window [%.2f, %.2f]",
                line["text"][:40],
                lrc_ts,
                lrc_ts - search_before_s,
                lrc_ts + search_after_s,
            )

        measurements.append(
            AnchorMeasurement(
                lrc_timestamp=lrc_ts,
                detected_onset=onset,
                offset=offset_val,
                line_text=line["text"],
                anchor_type=anchor_type,
                excluded=False,
            )
        )

    # --- Outlier rejection for first_line anchor ------------------------------
    # If section_boundary anchors agree with each other but the first_line
    # measurement is far off, it likely latched onto instrumental intro audio
    # rather than a real vocal onset.  Exclude it from the final calculation.
    boundary_offsets = [
        m["offset"]
        for m in measurements
        if m["anchor_type"] == "section_boundary" and m["offset"] is not None
    ]
    if len(boundary_offsets) >= 2:
        boundary_median = median(boundary_offsets)
        for m in measurements:
            if (
                m["anchor_type"] == "first_line"
                and m["offset"] is not None
                and abs(m["offset"] - boundary_median) > 0.4
            ):
                logger.debug(
                    "Excluding first_line anchor (offset %.3fs deviates %.3fs from "
                    "boundary median %.3fs)",
                    m["offset"],
                    abs(m["offset"] - boundary_median),
                    boundary_median,
                )
                m["excluded"] = True
                offsets.remove(m["offset"])

    # --- Compute summary ------------------------------------------------------
    if not offsets:
        return OffsetAnalysisResult(
            estimated_offset=None,
            confidence="insufficient",
            anchor_count=len(anchors),
            successful_anchors=0,
            anchors=measurements,
            max_deviation=None,
        )

    estimated_offset = round(median(offsets), 3)
    deviations = [abs(o - estimated_offset) for o in offsets]
    max_deviation = round(max(deviations), 3)
    n = len(offsets)

    if n >= 3 and max_deviation < 0.3:
        confidence: Literal["high", "medium", "low", "insufficient"] = "high"
    elif n >= 2 and max_deviation < 0.5:
        confidence = "medium"
    elif n >= 1:
        confidence = "low"
    else:
        confidence = "insufficient"

    logger.info(
        "Offset estimate: %.3fs  confidence=%s  anchors=%d/%d  max_dev=%.3fs",
        estimated_offset,
        confidence,
        n,
        len(anchors),
        max_deviation,
    )

    return OffsetAnalysisResult(
        estimated_offset=estimated_offset,
        confidence=confidence,
        anchor_count=len(anchors),
        successful_anchors=n,
        anchors=measurements,
        max_deviation=max_deviation,
    )


def shift_lrc_timestamps(content: str, shift_seconds: float) -> str:
    """Shift every LRC timestamp by a fixed number of seconds.

    Timestamps that would go negative are clamped to 0.  Non-timestamp lines
    (metadata tags, plain text) are passed through unchanged.

    Args:
        content: Raw LRC file content.
        shift_seconds: Seconds to add to every timestamp (negative = shift earlier).

    Returns:
        New LRC content string with all timestamps adjusted.
    """
    result_lines: list[str] = []
    for raw_line in content.splitlines():
        def _replace_ts(m: re.Match) -> str:
            mins = int(m.group(1))
            secs = int(m.group(2))
            frac_str = m.group(3)
            original_ts = _ts_to_seconds(mins, secs, frac_str)
            new_ts = max(0.0, original_ts + shift_seconds)
            return _seconds_to_lrc_ts(new_ts)

        new_line = _LRC_TS_PATTERN.sub(_replace_ts, raw_line)
        result_lines.append(new_line)

    return "\n".join(result_lines)
