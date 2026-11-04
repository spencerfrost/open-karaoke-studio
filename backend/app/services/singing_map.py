"""When the lead and the backing vocals are singing, measured from the separated stems.

The map needs no lyrics. Each stem is read on its own and kept separate, so a
use can tell "backing singing, lead silent" from "nobody singing".

Method "rms": RMS loudness per frame. A frame counts as singing when it is above
a share of the stem's own loud level (its 95th-percentile RMS) and above an
absolute floor. The relative threshold follows each stem's level; the floor stops
a near-silent stem's bleed and noise from reading as singing. Runs of singing
frames are joined across short gaps (breaths, consonants) and very short blips
are dropped.
"""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

METHOD = "rms"
SAMPLE_RATE = 16000
LEAD_STEM = "vocals.mp3"
BACKING_STEM = "backing_vocals.mp3"

Interval = tuple[float, float]


@dataclass(frozen=True)
class SingingMapParams:
    """The tunable numbers. Stored with every map so a rerun after tuning can be told apart."""

    hop_seconds: float = 0.02
    # Singing = above this share of the stem's 95th-percentile frame RMS...
    relative_threshold: float = 0.15
    # ...and above this absolute level (RMS in dBFS), whatever the stem's own level.
    floor_dbfs: float = -45.0
    # Quiet gaps shorter than this inside singing are closed.
    join_gap_seconds: float = 0.6
    # Singing runs shorter than this (after joining) are dropped.
    min_run_seconds: float = 0.25


DEFAULT_PARAMS = SingingMapParams()


def frame_rms(audio: np.ndarray, sample_rate: int, hop_seconds: float) -> np.ndarray:
    """RMS of each non-overlapping frame of `hop_seconds`; a trailing partial frame is kept."""
    hop = max(1, int(round(sample_rate * hop_seconds)))
    if audio.size == 0:
        return np.zeros(0, dtype=np.float32)
    frames = -(-audio.size // hop)  # ceil
    padded = np.zeros(frames * hop, dtype=np.float32)
    padded[: audio.size] = audio
    return np.sqrt(np.mean(padded.reshape(frames, hop) ** 2, axis=1))


def singing_intervals(
    audio: np.ndarray,
    sample_rate: int = SAMPLE_RATE,
    params: SingingMapParams = DEFAULT_PARAMS,
) -> list[Interval]:
    """Intervals (start, end), in seconds, where a mono stem is singing."""
    rms = frame_rms(audio, sample_rate, params.hop_seconds)
    if rms.size == 0:
        return []

    floor = 10 ** (params.floor_dbfs / 20)
    threshold = max(params.relative_threshold * float(np.percentile(rms, 95)), floor)
    singing = rms > threshold

    runs = _runs(singing)
    hop = params.hop_seconds
    duration = audio.size / sample_rate
    intervals = [(start * hop, min(end * hop, duration)) for start, end in runs]
    intervals = _join_close(intervals, params.join_gap_seconds)
    return [
        (round(start, 2), round(end, 2))
        for start, end in intervals
        if end - start >= params.min_run_seconds
    ]


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """(first, past-last) frame index of each run of True."""
    edges = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    return list(zip(starts.tolist(), ends.tolist()))


def _join_close(intervals: list[Interval], max_gap: float) -> list[Interval]:
    joined: list[Interval] = []
    for start, end in intervals:
        if joined and start - joined[-1][1] < max_gap:
            joined[-1] = (joined[-1][0], end)
        else:
            joined.append((start, end))
    return joined


def load_stem(path: Path) -> np.ndarray:
    """A stem as 16 kHz mono float32."""
    import librosa

    audio, _ = librosa.load(str(path), sr=SAMPLE_RATE, mono=True)
    return audio.astype(np.float32)


def measure_singing_map(
    song_dir: Path, params: SingingMapParams = DEFAULT_PARAMS
) -> dict[str, Any]:
    """Measure a song's singing map from its separated stems.

    Returns the JSON-ready map: `lead` and `backing` interval lists, `backing`
    None when the song has no backing stem, plus the method, its params and
    when it was measured, and the song's length.

    Raises FileNotFoundError when there is no lead vocal stem.
    """
    lead_path = song_dir / LEAD_STEM
    if not lead_path.exists():
        raise FileNotFoundError(lead_path)
    backing_path = song_dir / BACKING_STEM

    lead_audio = load_stem(lead_path)
    lead = singing_intervals(lead_audio, SAMPLE_RATE, params)
    backing: Optional[list[Interval]] = None
    if backing_path.exists():
        backing = singing_intervals(load_stem(backing_path), SAMPLE_RATE, params)

    logger.info(
        "Singing map: %d lead interval(s), %s backing interval(s)",
        len(lead),
        "no" if backing is None else len(backing),
    )
    return {
        "method": METHOD,
        "params": asdict(params),
        "lead": [list(interval) for interval in lead],
        "backing": None if backing is None else [list(i) for i in backing],
        "duration": round(lead_audio.size / SAMPLE_RATE, 2),
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Instrumental breaks from the map
# ---------------------------------------------------------------------------

# Same minimum and lead-in as the word-gap breaks in lyrics_alignment.py.
BREAK_MIN_SECONDS = 6.0
BREAK_LEAD_IN_SECONDS = 1.5
# A line without word timing is on screen from its timestamp to the next
# line's, as the TV shows it. The last line has no next line: this long.
UNTIMED_LAST_LINE_SECONDS = 10.0


@dataclass(frozen=True)
class LineWindow:
    """When a non-blank lyric line is on screen."""

    index: int  # source line index in the LRC, as word timings use
    start: float
    end: float
    text: str
    timed: bool  # from word timing; False = from the LRC timestamps


def line_windows(
    synced_lyrics: Optional[str], words: Optional[list[dict]] = None
) -> list[LineWindow]:
    """When each non-blank LRC line is on screen, sorted by start.

    A line with word timing runs from its first word's start to its last
    word's end; any other line from its timestamp to the next line's (blank
    lines included), the last one UNTIMED_LAST_LINE_SECONDS.
    """
    from app.services.lyrics_analysis import parse_lrc_lines

    if not synced_lyrics:
        return []
    lrc = sorted(parse_lrc_lines(synced_lyrics), key=lambda line: line["timestamp"])

    timed: dict[int, tuple[float, float]] = {}
    for word in words or []:
        index = word.get("line_index")
        if index is None:
            continue
        start, end = float(word["start"]), float(word["end"])
        if index in timed:
            timed[index] = (min(timed[index][0], start), max(timed[index][1], end))
        else:
            timed[index] = (start, end)

    windows = []
    for position, line in enumerate(lrc):
        text = line["text"].strip()
        if not text:
            continue
        index = line["line_index"]
        if index in timed:
            start, end = timed[index]
            windows.append(LineWindow(index, start, end, text, True))
            continue
        start = line["timestamp"]
        following = lrc[position + 1]["timestamp"] if position + 1 < len(lrc) else None
        end = start + UNTIMED_LAST_LINE_SECONDS
        if following is not None and following > start:
            end = following
        windows.append(LineWindow(index, start, end, text, False))
    return sorted(windows, key=lambda window: (window.start, window.index))


def union(*interval_lists: list[Interval]) -> list[Interval]:
    """Merge overlapping or touching intervals from any number of lists."""
    merged: list[Interval] = []
    for start, end in sorted(i for intervals in interval_lists for i in intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def intersect(a: list[Interval], b: list[Interval]) -> list[Interval]:
    """Where both lists cover."""
    a, b = union(a), union(b)
    result: list[Interval] = []
    i = j = 0
    while i < len(a) and j < len(b):
        start = max(a[i][0], b[j][0])
        end = min(a[i][1], b[j][1])
        if start < end:
            result.append((start, end))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return result


def subtract(a: list[Interval], b: list[Interval]) -> list[Interval]:
    """Where `a` covers and `b` doesn't."""
    result: list[Interval] = []
    b = union(b)
    for start, end in union(a):
        cursor = start
        for cut_start, cut_end in b:
            if cut_end <= cursor or cut_start >= end:
                continue
            if cut_start > cursor:
                result.append((cursor, cut_start))
            cursor = max(cursor, cut_end)
        if cursor < end:
            result.append((cursor, end))
    return result


def counted_singing(
    singing_map: dict[str, Any], windows: list[LineWindow]
) -> list[Interval]:
    """What counts as singing for breaks: the lead, plus the backing while a
    lyric line is on screen. Backing singing words the lyrics don't have (an
    ad-lib with no line) leaves the stretch a break."""
    lead = [tuple(i) for i in singing_map.get("lead") or []]
    backing = [tuple(i) for i in singing_map.get("backing") or []]
    on_screen = [(w.start, w.end) for w in windows]
    return union(lead, intersect(backing, on_screen))


def breaks_from_map(
    singing_map: dict[str, Any],
    windows: list[LineWindow],
    *,
    min_seconds: float = BREAK_MIN_SECONDS,
    lead_in_seconds: float = BREAK_LEAD_IN_SECONDS,
) -> list[dict[str, Any]]:
    """Instrumental breaks in the shape the player reads (`InstrumentalInterval`).

    A break is a stretch of `min_seconds` or more where nothing counts as
    singing (see `counted_singing`), leading into the first lyric line that
    starts after the stretch begins. A stretch after the last line has
    nothing to lead into and is left out.
    """
    if not windows:
        return []
    duration = float(singing_map.get("duration") or 0.0)
    singing = counted_singing(singing_map, windows)
    end_of_song = max(duration, singing[-1][1] if singing else 0.0)
    silent = subtract([(0.0, end_of_song)], singing)

    breaks = []
    for start, end in silent:
        length = end - start
        if length < min_seconds:
            continue
        next_line = next((w for w in windows if w.start >= start), None)
        if next_line is None:
            continue
        breaks.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(length, 3),
                "lead_in_start": round(max(start, end - lead_in_seconds), 3),
                "next_line_index": next_line.index,
                "confidence": round(min(1.0, length / 8.0), 3),
                "source": "singing_map",
            }
        )
    return breaks
