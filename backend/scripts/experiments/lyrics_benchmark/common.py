"""Shared pieces of the lyrics benchmark: paths, test set, text normalisation, scoring."""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

BENCH_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BENCH_DIR.parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Gitignored (backend/scripts/experiments/**/results/): the test set holds lyrics.
RESULTS_DIR = BENCH_DIR / "results"
TESTSET_PATH = RESULTS_DIR / "testset.json"
RUNS_DIR = RESULTS_DIR / "runs"

from app.services.lyrics_analysis import parse_lrc_lines  # noqa: E402


class TestSong(TypedDict):
    song_id: str
    title: str
    artist: str
    artist_key: str
    language: str
    language_source: str  # "db" or "detected"
    duration: float
    vocals_path: str
    synced_lyrics: str
    onset_activity: float  # share of LRC line starts with singing nearby


class RefLine(TypedDict):
    start: float
    text: str


def load_testset() -> list[TestSong]:
    if not TESTSET_PATH.exists():
        raise SystemExit(f"No test set at {TESTSET_PATH}; run build_testset.py first")
    return json.loads(TESTSET_PATH.read_text())["songs"]


def reference_lines(synced_lyrics: str) -> list[RefLine]:
    """Non-blank LRC lines in order. Every task scores against these."""
    return [
        RefLine(start=line["timestamp"], text=line["text"].strip())
        for line in parse_lrc_lines(synced_lyrics)
        if line["text"].strip()
    ]


def run_path(model: str, song_id: str) -> Path:
    return RUNS_DIR / model / f"{song_id}.json"


def read_run(model: str, song_id: str) -> dict[str, Any] | None:
    path = run_path(model, song_id)
    return json.loads(path.read_text()) if path.exists() else None


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------

_SECTION_TAG = re.compile(r"\[[^\]]*\]")  # [Chorus], [Verse 2: ...]
_PARENTHETICAL = re.compile(r"\([^)]*\)")  # (yeah), (backing line)
_QUOTES = str.maketrans({"’": "'", "‘": "'", "`": "'", "´": "'"})


def normalize_words(text: str, *, drop_parenthetical: bool) -> list[str]:
    """Lowercased words with punctuation and apostrophes removed.

    Apostrophes go entirely so "don't"/"dont" and "'cause"/"cause" match;
    hyphens split words. Numbers stay as written, so "2" vs "two" still
    counts as an error. `drop_parenthetical` removes "(...)" spans: in this
    library vocals.mp3 is the lead stem, and parentheses usually hold the
    backing vocals that went to the instrumental.
    """
    text = unicodedata.normalize("NFKC", text).translate(_QUOTES)
    text = _SECTION_TAG.sub(" ", text)
    if drop_parenthetical:
        text = _PARENTHETICAL.sub(" ", text)
    text = text.lower().replace("'", "").replace("-", " ")
    text = "".join(
        ch if unicodedata.category(ch)[0] in "LN" or ch.isspace() else " "
        for ch in text
    )
    return text.split()


# ---------------------------------------------------------------------------
# Word error rate
# ---------------------------------------------------------------------------


@dataclass
class EditCounts:
    substitutions: int = 0
    deletions: int = 0
    insertions: int = 0
    reference_words: int = 0

    @property
    def errors(self) -> int:
        return self.substitutions + self.deletions + self.insertions

    @property
    def wer(self) -> float:
        return self.errors / self.reference_words if self.reference_words else 0.0

    def __add__(self, other: EditCounts) -> EditCounts:
        return EditCounts(
            self.substitutions + other.substitutions,
            self.deletions + other.deletions,
            self.insertions + other.insertions,
            self.reference_words + other.reference_words,
        )


def edit_counts(reference: list[str], hypothesis: list[str]) -> EditCounts:
    """Levenshtein alignment of word lists, split into S/D/I.

    Deletions are words the model missed (often whole lines it didn't hear),
    insertions are words it made up (hallucinated or backing vocals).
    """
    rows, cols = len(reference) + 1, len(hypothesis) + 1
    cost = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        cost[i][0] = i
    for j in range(cols):
        cost[0][j] = j
    for i in range(1, rows):
        ref_word = reference[i - 1]
        row, above = cost[i], cost[i - 1]
        for j in range(1, cols):
            row[j] = min(
                above[j - 1] + (ref_word != hypothesis[j - 1]),
                above[j] + 1,
                row[j - 1] + 1,
            )

    counts = EditCounts(reference_words=len(reference))
    i, j = len(reference), len(hypothesis)
    while i > 0 or j > 0:
        if (
            i > 0
            and j > 0
            and cost[i][j]
            == cost[i - 1][j - 1] + (reference[i - 1] != hypothesis[j - 1])
        ):
            counts.substitutions += reference[i - 1] != hypothesis[j - 1]
            i, j = i - 1, j - 1
        elif i > 0 and cost[i][j] == cost[i - 1][j] + 1:
            counts.deletions += 1
            i -= 1
        else:
            counts.insertions += 1
            j -= 1
    return counts


# ---------------------------------------------------------------------------
# Alignment blocks
# ---------------------------------------------------------------------------

# Every aligner gets the same blocks: a run of lines and the audio window
# they're sung in. Window edges are put where the vocals stem is quiet,
# found from its loudness (no model involved), so a window never holds the
# end of another block's line even when the LRC is shifted by a second or
# two. Inside its window a model has to find each line itself.
BLOCKS_VERSION = 4
BLOCK_MAX_SECONDS = 45.0
# Search for a quiet stretch between line j and j+1 from just after line j
# starts until a little after line j+1 starts (LRCs are often late or early).
QUIET_SEARCH_AFTER_START = 0.5
QUIET_SEARCH_PAST_NEXT = 1.5
MIN_QUIET_SECONDS = 0.2
# Each side of a split keeps at least this much audio per line, so a split
# can't leave a line a sliver between two breaths.
MIN_SECONDS_PER_LINE = 1.5
SAMPLE_RATE = 16000
_HOP = 512


class Block(TypedDict):
    first_line: int
    last_line: int
    start: float
    end: float
    # False when no quiet stretch was found and an edge is the LRC time instead
    quiet_edges: bool


@dataclass(frozen=True)
class VocalActivity:
    loud: Any  # np.ndarray[bool], one value per frame
    frames_per_second: float
    duration: float

    def longest_quiet(self, start: float, end: float) -> tuple[float, float]:
        """(length, midpoint) of the longest quiet run in [start, end], in seconds."""
        lo = max(0, int(start * self.frames_per_second))
        hi = min(len(self.loud), int(end * self.frames_per_second))
        best_length, best_mid, run_start = 0, 0.0, None
        for frame in range(lo, hi + 1):
            quiet = frame < hi and not self.loud[frame]
            if quiet and run_start is None:
                run_start = frame
            elif not quiet and run_start is not None:
                if frame - run_start > best_length:
                    best_length = frame - run_start
                    best_mid = (run_start + frame) / 2
                run_start = None
        return best_length / self.frames_per_second, best_mid / self.frames_per_second


def vocal_activity(audio: Any) -> VocalActivity:
    """Loud/quiet per frame of a 16 kHz vocals stem (loud = above 15% of its 95th percentile RMS)."""
    import librosa
    import numpy as np

    rms = librosa.feature.rms(y=audio, hop_length=_HOP)[0]
    return VocalActivity(
        loud=rms > 0.15 * float(np.percentile(rms, 95)),
        frames_per_second=SAMPLE_RATE / _HOP,
        duration=len(audio) / SAMPLE_RATE,
    )


def load_vocals_16k(path: str) -> Any:
    import librosa
    import numpy as np

    audio, _ = librosa.load(path, sr=SAMPLE_RATE, mono=True)
    return audio.astype(np.float32)


def build_blocks(lines: list[RefLine], activity: VocalActivity) -> list[Block]:
    """Split the song at quiet stretches until every window is at most BLOCK_MAX_SECONDS.

    The first window starts at 0 and the last ends with the song. Each split
    goes at the longest quiet run between two consecutive lines (ties to the
    one nearest the middle), so big instrumental breaks are used first.
    """

    def fits(
        j: int, edge: float, first: int, last: int, start: float, end: float
    ) -> bool:
        return edge - start >= MIN_SECONDS_PER_LINE * (
            j - first + 1
        ) and end - edge >= MIN_SECONDS_PER_LINE * (last - j)

    def split(
        first: int,
        last: int,
        start: float,
        end: float,
        quiet_start: bool,
        quiet_end: bool,
    ) -> list[Block]:
        whole = [
            Block(
                first_line=first,
                last_line=last,
                start=round(start, 3),
                end=round(end, 3),
                quiet_edges=quiet_start and quiet_end,
            )
        ]
        if first == last or end - start <= BLOCK_MAX_SECONDS:
            return whole
        middle = (start + end) / 2
        best: tuple[float, float, int, float] | None = (
            None  # (length, -distance, j, edge)
        )
        for j in range(first, last):
            length, mid = activity.longest_quiet(
                max(start, lines[j]["start"] + QUIET_SEARCH_AFTER_START),
                min(end, lines[j + 1]["start"] + QUIET_SEARCH_PAST_NEXT),
            )
            if length < MIN_QUIET_SECONDS or not fits(j, mid, first, last, start, end):
                continue
            candidate = (round(length, 2), -abs(mid - middle), j, mid)
            if best is None or candidate > best:
                best = candidate
        if best is not None:
            _, _, j, edge = best
            quiet_edge = True
        else:
            # Singing never stops: cut at an LRC line time, nearest the middle.
            cuts = [
                j
                for j in range(first, last)
                if fits(j, lines[j + 1]["start"], first, last, start, end)
            ]
            if not cuts:
                return whole
            j = min(cuts, key=lambda c: abs(lines[c + 1]["start"] - middle))
            edge, quiet_edge = lines[j + 1]["start"], False
        return split(first, j, start, edge, quiet_start, quiet_edge) + split(
            j + 1, last, edge, end, quiet_edge, quiet_end
        )

    return split(0, len(lines) - 1, 0.0, activity.duration, True, True)


def song_blocks(song: TestSong) -> list[Block]:
    """The song's blocks, computed once and cached so every aligner gets the same ones."""
    path = RESULTS_DIR / "blocks" / f"{song['song_id']}.json"
    if path.exists():
        cached = json.loads(path.read_text())
        if cached["version"] == BLOCKS_VERSION:
            return cached["blocks"]
    blocks = build_blocks(
        reference_lines(song["synced_lyrics"]),
        vocal_activity(load_vocals_16k(song["vocals_path"])),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": BLOCKS_VERSION, "blocks": blocks}, indent=1))
    return blocks
