"""Shared pieces of the song versions benchmark: paths, test set, lines, intervals.

See docs/plans/2026-11-10-song-versions.md.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Literal, NotRequired, Optional, TypedDict

BENCH_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BENCH_DIR.parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.lyrics_analysis import parse_lrc_lines  # noqa: E402
from app.services.lyrics_retiming import _tokens  # noqa: E402
from app.services.singing_map import intersect, subtract, union  # noqa: E402,F401

# Gitignored (backend/scripts/experiments/**/results/): the test set holds lyrics.
RESULTS_DIR = BENCH_DIR / "results"
TESTSET_PATH = RESULTS_DIR / "testset.json"
TRANSCRIPTS_DIR = RESULTS_DIR / "transcripts"
RUNS_DIR = RESULTS_DIR / "runs"
SYNTHETIC_DIR = RESULTS_DIR / "synthetic"
REPORT_PATH = RESULTS_DIR / "report.md"

LIBRARY_DIR = Path(
    os.getenv("LIBRARY_DIR", str(BACKEND_DIR.parent / "karaoke_library"))
)

# The transcription models every ASR method runs on, by the lyrics benchmark's names.
ASR_MODELS = {
    "whisper-small": "small",
    "whisper-large-v3-turbo": "large-v3-turbo",
}
DEFAULT_ASR = "whisper-small"

Interval = tuple[float, float]
SongKind = Literal["real", "control", "synthetic"]
LineSource = Literal["album", "heard"]


class StoredTiming(TypedDict):
    """What the app stores for a song today: its LRC and its word timing."""

    lrc: str
    words: list[dict[str, Any]]
    mean_score: Optional[float]


class TruthLine(TypedDict):
    """A line of a synthetic version as it is really sung."""

    start: float
    text: str
    source: LineSource
    # Index into the song's album lines; None for a line the album lyrics lack.
    album_index: Optional[int]


class TestSong(TypedDict):
    song_id: str
    kind: SongKind
    # Why it is in the set: "pair", "untimed singing", "added", "control", or a
    # synthetic recipe name.
    picked_as: str
    title: str
    artist: str
    duration: Optional[float]
    # The folder holding vocals.mp3 (and backing_vocals.mp3 when there is one).
    song_dir: str
    language: str
    # "pair" (taken from the album version), "song", "manual" or "default".
    language_source: str
    # The album lyrics every method starts from, as LRC.
    album_lrc: str
    # The song the album lyrics came from (itself, or its pair).
    album_from: str
    # Other versions of the same song in the library.
    pair_ids: list[str]
    # Today's stored timing; None for synthetic songs.
    today: Optional[StoredTiming]
    # Singing map intervals; None when the song has no map.
    lead: Optional[list[Interval]]
    backing: Optional[list[Interval]]
    # Synthetic songs only.
    truth: Optional[list[TruthLine]]
    # Seconds of lead singing before the first / after the last timed word today.
    untimed_before: Optional[float]
    untimed_after: Optional[float]
    # A real version transcribed by ear (add_version_lyrics.py): the truth only
    # covers this stretch, and the version's own lyrics as LRC.
    truth_span: NotRequired[list[float]]
    version_lrc: NotRequired[str]


class AlbumLine(TypedDict):
    # Position among the album's non-blank lines: what `album_index` means everywhere.
    index: int
    # Position in parse_lrc_lines(album_lrc), blank lines included: what the
    # app's stored words call `line_index`.
    lrc_index: int
    time: float
    text: str


class PlanLine(TypedDict):
    text: str
    source: LineSource
    album_index: Optional[int]


class PlanChunk(TypedDict):
    """Lines aligned together within one stretch of the audio."""

    start: float
    end: float
    lines: list[PlanLine]


class Plan(TypedDict, total=False):
    """What a method decides.

    `stored`: use today's timing as is. `lrc`: force-align this LRC the usual
    way. `chunks`: force-align each chunk's lines inside its stretch. `lrc` and
    `chunks` can come together: the chunks are lines outside the LRC.
    """

    stored: StoredTiming
    lrc: str
    lrc_lines: list[PlanLine]
    chunks: list[PlanChunk]
    notes: dict[str, Any]


def load_testset() -> list[TestSong]:
    if not TESTSET_PATH.exists():
        raise SystemExit(f"No test set at {TESTSET_PATH}; run build_testset.py first")
    return json.loads(TESTSET_PATH.read_text())["songs"]


def vocals_path(song: TestSong) -> Path:
    return Path(song["song_dir"]) / "vocals.mp3"


def album_lines(lrc: str) -> list[AlbumLine]:
    """The album's sung lines, in order, with both index conventions."""
    lines: list[AlbumLine] = []
    for lrc_index, line in enumerate(parse_lrc_lines(lrc)):
        if line["text"].strip() and _tokens(line["text"]):
            lines.append(
                AlbumLine(
                    index=len(lines),
                    lrc_index=lrc_index,
                    time=line["timestamp"],
                    text=line["text"].strip(),
                )
            )
    return lines


def tokens(text: str) -> list[str]:
    """Words as the app's re-timer compares them: lowercase, no punctuation."""
    return _tokens(text)


def transcript_path(asr: str, song_id: str) -> Path:
    return TRANSCRIPTS_DIR / asr / f"{song_id}.json"


def load_transcript(asr: str, song_id: str) -> Optional[dict[str, Any]]:
    path = transcript_path(asr, song_id)
    return json.loads(path.read_text()) if path.exists() else None


def run_dir(method: str, asr: Optional[str], lyrics: str = "album") -> Path:
    """results/runs/<method>[@<asr>][+version-lyrics]."""
    name = f"{method}@{asr}" if asr else method
    return RUNS_DIR / (name + ("+version-lyrics" if lyrics == "version" else ""))


def total(intervals: list[Interval]) -> float:
    return sum(max(0.0, b - a) for a, b in intervals)


def sung(song: TestSong) -> list[Interval]:
    """Lead and backing singing together."""
    return union(
        [(a, b) for a, b in song["lead"] or []],
        [(a, b) for a, b in song["backing"] or []],
    )


def line_spans(words: list[dict[str, Any]]) -> dict[int, Interval]:
    """Each line's first word start to last word end, by line_index."""
    spans: dict[int, Interval] = {}
    for word in words:
        index = word["line_index"]
        start, end = spans.get(index, (word["start"], word["end"]))
        spans[index] = (min(start, word["start"]), max(end, word["end"]))
    return spans
