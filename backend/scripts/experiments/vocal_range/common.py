"""Shared pieces of the vocal range benchmark: paths, test set, contours, notes."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypedDict

import numpy as np

BENCH_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BENCH_DIR.parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Gitignored (backend/scripts/experiments/**/results/).
RESULTS_DIR = BENCH_DIR / "results"
TESTSET_PATH = RESULTS_DIR / "testset.json"
CONTOURS_DIR = RESULTS_DIR / "contours"
# Committed: note names and where they came from, nothing copyrighted.
REFERENCE_PATH = BENCH_DIR / "reference.json"

Interval = tuple[float, float]


class TestSong(TypedDict):
    song_id: str
    title: str
    artist: str
    duration: Optional[float]
    vocals_path: str
    # What the app stores today; may predate round() (see the plan's status).
    stored_low: Optional[str]
    stored_high: Optional[str]
    # Why it is in the set: "named" (the plan's test songs) or a width bucket.
    picked_as: str
    # The singing map's lead intervals; None when the song has no map.
    lead_intervals: Optional[list[Interval]]
    # Each non-blank synced-lyrics line as (start, end): end is the next line's
    # start, capped. Times only; no lyric text is kept. None without synced lyrics.
    lyric_lines: Optional[list[Interval]]


class Reference(TypedDict, total=False):
    low: Optional[str]
    high: Optional[str]
    # "sung", "rapped", "spoken", "mixed" (rap plus a sung hook), "instrumental"
    kind: str
    source: str
    url: str
    notes: str


@dataclass(frozen=True)
class Contour:
    """A pitch track: one entry per frame."""

    times: np.ndarray  # seconds, frame centres
    f0: np.ndarray  # Hz, NaN where unvoiced
    voiced_flag: np.ndarray  # bool
    voiced_prob: np.ndarray  # 0..1
    hop_seconds: float

    @property
    def midi(self) -> np.ndarray:
        with np.errstate(divide="ignore", invalid="ignore"):
            return 69 + 12 * np.log2(self.f0 / 440.0)


def load_testset() -> list[TestSong]:
    if not TESTSET_PATH.exists():
        raise SystemExit(f"No test set at {TESTSET_PATH}; run build_testset.py first")
    return json.loads(TESTSET_PATH.read_text())["songs"]


def load_reference() -> dict[str, Reference]:
    if not REFERENCE_PATH.exists():
        return {}
    data = json.loads(REFERENCE_PATH.read_text())
    return {k: v for k, v in data.items() if not k.startswith("_")}


def contour_path(setting: str, song_id: str) -> Path:
    return CONTOURS_DIR / setting / f"{song_id}.npz"


def load_contour(setting: str, song_id: str) -> Optional[Contour]:
    path = contour_path(setting, song_id)
    if not path.exists():
        return None
    data = np.load(path)
    return Contour(
        times=data["times"],
        f0=data["f0"],
        voiced_flag=data["voiced_flag"],
        voiced_prob=data["voiced_prob"],
        hop_seconds=float(data["hop_seconds"]),
    )


# Sharps as the app writes them (librosa's default unicode output).
_NAMES = ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"]
_LETTER = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi_to_note(midi: int) -> str:
    return f"{_NAMES[midi % 12]}{midi // 12 - 1}"


def note_to_midi(note: str) -> int:
    """'G3', 'G#3', 'G♯3', 'Ab3', 'A♭3' -> MIDI number."""
    note = note.strip().replace("♯", "#").replace("♭", "b")
    letter, rest = note[0].upper(), note[1:]
    shift = 0
    while rest and rest[0] in "#b":
        shift += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return _LETTER[letter] + shift + 12 * (int(rest) + 1)


def inside(times: np.ndarray, intervals: list[Interval]) -> np.ndarray:
    """Mask of `times` that fall inside any of the sorted `intervals`."""
    mask = np.zeros(times.shape, dtype=bool)
    if not intervals:
        return mask
    starts = np.array([a for a, _ in intervals])
    ends = np.array([b for _, b in intervals])
    idx = np.searchsorted(starts, times, side="right") - 1
    ok = idx >= 0
    mask[ok] = times[ok] < ends[idx[ok]]
    return mask
