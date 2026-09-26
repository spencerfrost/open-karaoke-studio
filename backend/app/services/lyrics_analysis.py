"""
Lyrics section break analysis.

Analyzes synced LRC lyrics to detect where section breaks (verse→chorus, etc.)
should be inserted. Uses text-based and timing-based methods, each producing
candidates with confidence scores that are fused into a final result.
"""

import logging
import re
from collections import defaultdict
from statistics import median
from typing import TypedDict

logger = logging.getLogger(__name__)

LRC_LINE_PATTERN = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{2,3}))?\]\s*(.*)")


class LrcLine(TypedDict):
    timestamp: float
    text: str
    line_index: int


class SectionBreakCandidate(TypedDict):
    after_line_index: int
    timestamp: float
    confidence: float
    methods: list[str]
    reasons: list[str]
    before_text: str
    after_text: str


class AnalysisStats(TypedDict):
    median_gap: float | None
    repeated_groups_found: int
    candidates_by_method: dict[str, int]


class AnalysisResult(TypedDict):
    total_lines: int
    existing_breaks: int
    candidates: list[SectionBreakCandidate]
    modified_lrc: str
    stats: AnalysisStats


def parse_lrc_lines(content: str) -> list[LrcLine]:
    """Parse LRC content into structured lines with timestamps."""
    lines: list[LrcLine] = []
    for i, raw_line in enumerate(content.strip().splitlines()):
        match = LRC_LINE_PATTERN.match(raw_line.strip())
        if not match:
            continue
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        centiseconds_str = match.group(3) or "0"
        # Handle both 2-digit (centiseconds) and 3-digit (milliseconds) formats
        if len(centiseconds_str) == 3:
            fractional = int(centiseconds_str) / 1000.0
        else:
            fractional = int(centiseconds_str) / 100.0
        timestamp = minutes * 60.0 + seconds + fractional

        lines.append(
            LrcLine(timestamp=timestamp, text=match.group(4).strip(), line_index=i)
        )
    return lines


def _normalize_text(text: str) -> str:
    """Normalize lyrics text for comparison."""
    return re.sub(r"\s+", " ", text.lower().strip())


def analyze_timing_gaps(
    lines: list[LrcLine], threshold_multiplier: float = 2.0
) -> list[SectionBreakCandidate]:
    """Find timing gaps between consecutive lines that are significantly larger than median."""
    # Filter to lines with actual text
    text_lines = [l for l in lines if l["text"]]
    if len(text_lines) < 3:
        return []

    # Compute gaps between consecutive text lines
    gaps: list[tuple[int, int, float]] = []  # (idx_a, idx_b, gap_seconds)
    for i in range(len(text_lines) - 1):
        gap = text_lines[i + 1]["timestamp"] - text_lines[i]["timestamp"]
        gaps.append((i, i + 1, gap))

    if not gaps:
        return []

    median_gap = median(g[2] for g in gaps)
    if median_gap <= 0:
        return []

    threshold = median_gap * threshold_multiplier
    candidates: list[SectionBreakCandidate] = []

    for idx_a, idx_b, gap in gaps:
        if gap < threshold:
            continue

        ratio = gap / median_gap
        confidence = min(1.0, gap / (median_gap * 4.0))
        # Place break timestamp at the midpoint
        break_ts = text_lines[idx_a]["timestamp"] + gap / 2.0

        candidates.append(
            SectionBreakCandidate(
                after_line_index=text_lines[idx_a]["line_index"],
                timestamp=break_ts,
                confidence=round(confidence, 2),
                methods=["timing_gap"],
                reasons=[f"{gap:.1f}s gap, median is {median_gap:.1f}s ({ratio:.1f}x)"],
                before_text=text_lines[idx_a]["text"],
                after_text=text_lines[idx_b]["text"],
            )
        )

    return candidates


def _group_consecutive_starts(starts: list[int]) -> list[tuple[int, int]]:
    """Group a sorted list of start indices into (first, last) pairs of consecutive runs.

    Used to collapse overlapping matches of identical content (e.g. a run of 9
    identical lines produces 8 overlapping 2-line starts) into a single span so
    only the outermost boundaries are considered.
    """
    if not starts:
        return []
    runs: list[tuple[int, int]] = []
    run_start = starts[0]
    run_last = starts[0]
    for s in starts[1:]:
        if s == run_last + 1:
            run_last = s
        else:
            runs.append((run_start, run_last))
            run_start = s
            run_last = s
    runs.append((run_start, run_last))
    return runs


def analyze_text_repetition(
    lines: list[LrcLine],
    min_group_size: int = 2,
    max_group_size: int = 6,
    min_repetitions: int = 2,
) -> list[SectionBreakCandidate]:
    """Find repeated groups of lines (choruses) and mark boundaries around them."""
    text_lines = [l for l in lines if l["text"]]
    if len(text_lines) < min_group_size * min_repetitions:
        return []

    normalized = [_normalize_text(l["text"]) for l in text_lines]

    # Pass 1: collect all repeated groups across every size.
    group_data: dict[int, dict[str, list[int]]] = {}
    for group_size in range(min_group_size, min(max_group_size + 1, len(text_lines))):
        occurrences: dict[str, list[int]] = defaultdict(list)
        for i in range(len(normalized) - group_size + 1):
            key = "\n".join(normalized[i : i + group_size])
            occurrences[key].append(i)
        group_data[group_size] = {
            k: v for k, v in occurrences.items() if len(v) >= min_repetitions
        }

    # Pass 2: build interior-position suppression map.
    # For a repeated span [s, e], positions s..e-1 are "interior" — a candidate
    # boundary placed there would be inside the block, not at its edge.
    # pos_max_interior_size[p] = the largest group_size whose interior includes p.
    # A candidate at position p from group_size G is suppressed when a strictly
    # larger group already claims p as interior.
    pos_max_interior_size: dict[int, int] = defaultdict(int)
    for group_size, groups in group_data.items():
        for starts in groups.values():
            for start in starts:
                end = start + group_size - 1
                for p in range(start, end):  # interior: start to end-1 inclusive
                    if group_size > pos_max_interior_size[p]:
                        pos_max_interior_size[p] = group_size

    # Pass 3: generate candidates, applying both fixes.
    best_candidates: dict[int, SectionBreakCandidate] = {}

    for group_size in range(min_group_size, min(max_group_size + 1, len(text_lines))):
        if group_size not in group_data:
            continue

        for key, start_indices in group_data[group_size].items():
            repetition_count = len(start_indices)
            confidence = round(
                min(1.0, (group_size / 4.0) * (repetition_count / 3.0)), 2
            )

            # Fix 2: collapse consecutive starts into runs so that a block of N
            # identical adjacent lines emits candidates only at the outermost
            # boundaries, not at every overlapping interior pair.
            runs = _group_consecutive_starts(start_indices)

            for first_start, last_start in runs:
                actual_end = last_start + group_size - 1

                # Candidate BEFORE the group (if not at the start of text)
                if first_start > 0:
                    before_pos = first_start - 1
                    # Fix 1: suppress if a larger repeated group has this position
                    # as an interior point — it's not a real section boundary.
                    if pos_max_interior_size.get(before_pos, 0) > group_size:
                        continue
                    before_line = text_lines[before_pos]
                    first_line = text_lines[first_start]
                    line_idx = before_line["line_index"]
                    gap = first_line["timestamp"] - before_line["timestamp"]
                    break_ts = before_line["timestamp"] + gap / 2.0

                    if (
                        line_idx not in best_candidates
                        or best_candidates[line_idx]["confidence"] < confidence
                    ):
                        best_candidates[line_idx] = SectionBreakCandidate(
                            after_line_index=line_idx,
                            timestamp=break_ts,
                            confidence=confidence,
                            methods=["text_repetition"],
                            reasons=[
                                f"Start of repeated {group_size}-line group ({repetition_count}x)"
                            ],
                            before_text=before_line["text"],
                            after_text=first_line["text"],
                        )

                # Candidate AFTER the group (if not at the end of text)
                if actual_end < len(text_lines) - 1:
                    after_pos = actual_end
                    # Fix 1: suppress if interior to a larger repeated group.
                    if pos_max_interior_size.get(after_pos, 0) > group_size:
                        continue
                    last_line = text_lines[actual_end]
                    next_line = text_lines[actual_end + 1]
                    line_idx = last_line["line_index"]
                    gap = next_line["timestamp"] - last_line["timestamp"]
                    break_ts = last_line["timestamp"] + gap / 2.0

                    if (
                        line_idx not in best_candidates
                        or best_candidates[line_idx]["confidence"] < confidence
                    ):
                        best_candidates[line_idx] = SectionBreakCandidate(
                            after_line_index=line_idx,
                            timestamp=break_ts,
                            confidence=confidence,
                            methods=["text_repetition"],
                            reasons=[
                                f"End of repeated {group_size}-line group ({repetition_count}x)"
                            ],
                            before_text=last_line["text"],
                            after_text=next_line["text"],
                        )

    return list(best_candidates.values())


def fuse_candidates(
    *candidate_lists: list[SectionBreakCandidate],
) -> list[SectionBreakCandidate]:
    """Merge candidates from multiple methods, boosting confidence when they agree."""
    # Group by after_line_index
    by_line: dict[int, list[SectionBreakCandidate]] = defaultdict(list)
    for candidates in candidate_lists:
        for c in candidates:
            by_line[c["after_line_index"]].append(c)

    fused: list[SectionBreakCandidate] = []
    for line_idx, group in sorted(by_line.items()):
        if len(group) == 1:
            fused.append(group[0])
            continue

        # Multiple methods agree on this boundary — merge
        all_methods: list[str] = []
        all_reasons: list[str] = []
        max_confidence = 0.0

        for c in group:
            all_methods.extend(c["methods"])
            all_reasons.extend(c["reasons"])
            max_confidence = max(max_confidence, c["confidence"])

        # Boost confidence when methods agree
        unique_methods = list(dict.fromkeys(all_methods))  # dedupe, preserve order
        if len(unique_methods) > 1:
            boosted = min(1.0, max_confidence + 0.25)
        else:
            boosted = max_confidence

        base = group[0]
        fused.append(
            SectionBreakCandidate(
                after_line_index=line_idx,
                timestamp=base["timestamp"],
                confidence=round(boosted, 2),
                methods=unique_methods,
                reasons=all_reasons,
                before_text=base["before_text"],
                after_text=base["after_text"],
            )
        )

    fused.sort(key=lambda c: c["timestamp"])
    return fused


def _build_modified_lrc(
    content: str,
    lines: list[LrcLine],
    candidates: list[SectionBreakCandidate],
    min_confidence: float = 0.3,
) -> str:
    """Insert empty timestamped lines at candidate positions in the original LRC."""
    filtered = [c for c in candidates if c["confidence"] >= min_confidence]
    if not filtered:
        return content

    # Build a set of line indices after which to insert breaks
    break_after: dict[int, float] = {}
    for c in filtered:
        idx = c["after_line_index"]
        # Don't insert if there's already a break (empty line) right after
        next_lines = [l for l in lines if l["line_index"] == idx + 1]
        if next_lines and not next_lines[0]["text"]:
            continue
        break_after[idx] = c["timestamp"]

    if not break_after:
        return content

    raw_lines = content.strip().splitlines()
    result: list[str] = []

    for i, raw_line in enumerate(raw_lines):
        result.append(raw_line)
        if i in break_after:
            ts = break_after[i]
            minutes = int(ts // 60)
            seconds = ts % 60
            result.append(f"[{minutes:02d}:{seconds:05.2f}]")

    return "\n".join(result)


def analyze_lyrics(lrc_content: str, min_confidence: float = 0.3) -> AnalysisResult:
    """Run all analysis methods on LRC content and return fused results."""
    lines = parse_lrc_lines(lrc_content)

    if not lines:
        return AnalysisResult(
            total_lines=0,
            existing_breaks=0,
            candidates=[],
            modified_lrc=lrc_content,
            stats=AnalysisStats(
                median_gap=None,
                repeated_groups_found=0,
                candidates_by_method={},
            ),
        )

    existing_breaks = sum(1 for l in lines if not l["text"])

    timing_candidates = analyze_timing_gaps(lines)
    repetition_candidates = analyze_text_repetition(lines)
    fused = fuse_candidates(timing_candidates, repetition_candidates)

    # Count repeated groups for stats
    text_lines = [l for l in lines if l["text"]]
    repeated_groups = 0
    if len(text_lines) >= 4:
        normalized = [_normalize_text(l["text"]) for l in text_lines]
        for group_size in range(2, min(7, len(text_lines))):
            seen: dict[str, int] = defaultdict(int)
            for i in range(len(normalized) - group_size + 1):
                key = "\n".join(normalized[i : i + group_size])
                seen[key] += 1
            repeated_groups += sum(1 for count in seen.values() if count >= 2)

    # Compute median gap for stats
    median_gap = None
    if len(text_lines) >= 2:
        gaps = [
            text_lines[i + 1]["timestamp"] - text_lines[i]["timestamp"]
            for i in range(len(text_lines) - 1)
        ]
        median_gap = round(median(gaps), 2)

    modified_lrc = _build_modified_lrc(lrc_content, lines, fused, min_confidence)

    timing_count = sum(1 for c in timing_candidates)
    repetition_count = sum(1 for c in repetition_candidates)

    return AnalysisResult(
        total_lines=len(lines),
        existing_breaks=existing_breaks,
        candidates=fused,
        modified_lrc=modified_lrc,
        stats=AnalysisStats(
            median_gap=median_gap,
            repeated_groups_found=repeated_groups,
            candidates_by_method={
                "timing_gap": timing_count,
                "text_repetition": repetition_count,
            },
        ),
    )
