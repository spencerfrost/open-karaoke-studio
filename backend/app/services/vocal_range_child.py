"""Measure a lead vocal's pitch range; run as a child process, not imported.

librosa's pyin runs numba-compiled loops that never release the GIL, so run in
a worker thread it starves every other thread in the process for the minute or
so a song takes: a Celery worker stops answering pings and picking up tasks,
and the API stops serving requests. In a process of its own it can only take
its own GIL. detect_vocal_range in audio.py starts this file by path, so the
child imports librosa and numpy and nothing from the app.

The method ("lyrics-v2", chosen by ear on the vocal range benchmark in
scripts/experiments/vocal_range/): pyin's pitch track, kept only where the
singing map says the lead sings and a lyric line is on screen, joined into
held notes. The range runs from the lowest to the highest note held for a
quarter second in total, after dropping top notes pyin reads an octave up. A
lead that's rarely pitched is "rapped" and gets no range.

Usage: python vocal_range_child.py <vocals file>, with the song's context on
stdin as JSON: {"lead": [[start, end], ...], "lyric_lines": [[start, end], ...]
or null}. Prints one JSON object on stdout: {"low": "G2", "high": "E5",
"label": null, "detail": {...}}. With no range, low and high are null and
label says why ("rapped", "no lead found", "one note"), or is null when no
note was held long enough.
"""

import json
import sys
from dataclasses import dataclass
from typing import Optional

import librosa
import numpy as np

METHOD = "lyrics-v2"
SAMPLE_RATE = 22050
HOP_LENGTH = 512
# Below a bass singer's lowest note and above a soprano's highest.
LOWEST_NOTE = "C2"
HIGHEST_NOTE = "C7"
# pyin's probability that a frame is voiced; below this the pitch is a guess.
MIN_VOICED_PROBABILITY = 0.75

# Frames join one note while each stays this close (semitones) to the note so far.
NOTE_TOLERANCE = 0.5
# A gap of up to this many unvoiced frames doesn't end a note.
NOTE_MAX_GAP_FRAMES = 2
# A note must be held at least this long to count...
MIN_NOTE_SECONDS = 0.15
# ...and an end of the range must be sung for at least this long in total.
MIN_END_SECONDS = 0.25

# Labels. Pitched share: lead-singing frames pyin is fairly sure are pitched.
# Rap and speech sat at 1-9% on the test songs, sung songs at 16% and up; by
# ear no cut separates them cleanly, and 7% misses the fewest.
PITCHED_PROBABILITY = 0.5
RAPPED_BELOW_SHARE = 0.07
# Less lead singing than this (s): the lead stem holds no singer to measure.
NO_LEAD_BELOW_SECONDS = 10.0

# Octave context: a top note held an octave above the highest note sung within
# CONTEXT_SECONDS of it, and well above their median, is pyin reading it an
# octave up.
CONTEXT_SECONDS = 4.0
OCTAVE_ABOVE_NEAREST = (11, 13)
OCTAVE_ABOVE_MEDIAN = 13

# The moments that set each end, longest first, so a person can listen to them.
MOMENTS_PER_END = 3

# Sharps as the app writes them (librosa's default unicode output).
_NAMES = ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"]

Interval = tuple[float, float]


@dataclass
class Note:
    start: float
    end: float
    midi: int


def midi_to_note(midi: int) -> str:
    return f"{_NAMES[midi % 12]}{midi // 12 - 1}"


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


def join_notes(times: np.ndarray, midi: np.ndarray, hop: float) -> list[Note]:
    """Runs of frames that hold one pitch, at least MIN_NOTE_SECONDS long.

    `times` and `midi` are the kept frames only, in order.
    """
    notes: list[Note] = []
    if times.size == 0:
        return notes
    run_start = 0
    max_gap = hop * (NOTE_MAX_GAP_FRAMES + 1) + 1e-6

    def close(first: int, past: int) -> None:
        start, end = float(times[first]), float(times[past - 1]) + hop
        if end - start >= MIN_NOTE_SECONDS:
            notes.append(Note(start, end, round(float(np.median(midi[first:past])))))

    for i in range(1, times.size):
        centre = float(np.median(midi[run_start:i]))
        if times[i] - times[i - 1] > max_gap or abs(midi[i] - centre) > NOTE_TOLERANCE:
            close(run_start, i)
            run_start = i
    close(run_start, times.size)
    return notes


def _held(notes: list[Note]) -> dict[int, float]:
    held: dict[int, float] = {}
    for note in notes:
        held[note.midi] = held.get(note.midi, 0.0) + note.end - note.start
    return held


def octave_up(note: Note, context: list[Note]) -> bool:
    """Whether `note` looks like pyin reading the singer an octave up."""
    near = [
        n.midi
        for n in context
        if n.end > note.start - CONTEXT_SECONDS
        and n.start < note.end + CONTEXT_SECONDS
        and not (n.start >= note.start - 0.01 and n.end <= note.end + 0.01)
    ]
    if not near:
        return False
    above_nearest = note.midi - max(near)
    return (
        OCTAVE_ABOVE_NEAREST[0] <= above_nearest <= OCTAVE_ABOVE_NEAREST[1]
        and note.midi - float(np.median(near)) >= OCTAVE_ABOVE_MEDIAN
    )


def drop_octave_tops(notes: list[Note], context: list[Note]) -> tuple[list[Note], int]:
    """Drop top notes that read an octave up, until the top one doesn't."""
    dropped = 0
    while True:
        counted = [m for m, sec in _held(notes).items() if sec >= MIN_END_SECONDS]
        if not counted:
            break
        top = max(counted)
        bad = [n for n in notes if n.midi == top and octave_up(n, context)]
        if not bad:
            break
        notes = [n for n in notes if n not in bad]
        dropped += len(bad)
    return notes, dropped


def _moments(notes: list[Note], pitch: int) -> list[dict]:
    at = sorted(
        (n for n in notes if n.midi == pitch),
        key=lambda n: n.end - n.start,
        reverse=True,
    )
    return [
        {"start": round(n.start, 2), "duration": round(n.end - n.start, 2)}
        for n in at[:MOMENTS_PER_END]
    ]


def decide_range(
    times: np.ndarray,
    f0: np.ndarray,
    voiced_flag: np.ndarray,
    voiced_prob: np.ndarray,
    hop: float,
    lead: list[Interval],
    lyric_lines: Optional[list[Interval]],
) -> dict:
    """The range from a pitch track and the song's context. See the module docstring."""
    with np.errstate(divide="ignore", invalid="ignore"):
        midi_all = 69 + 12 * np.log2(f0 / 440.0)
    voiced = voiced_flag & ~np.isnan(f0)
    confident = voiced & (voiced_prob > MIN_VOICED_PROBABILITY)
    in_lead = inside(times, lead)

    gates = ["lead"]
    mask = confident & in_lead
    if lyric_lines:
        mask &= inside(times, lyric_lines)
        gates.append("lyrics")

    notes = join_notes(times[mask], midi_all[mask], hop)
    lead_seconds = sum(b - a for a, b in lead)
    pitched = in_lead & voiced & (voiced_prob > PITCHED_PROBABILITY)
    # Rounded before the rapped test, as the benchmark that set the cut did.
    pitched_share = (
        round(float(pitched.sum() / in_lead.sum()), 3) if in_lead.any() else 0.0
    )
    detail: dict = {
        "method": METHOD,
        "gates": gates,
        "lead_seconds": round(lead_seconds, 1),
        "pitched_share": pitched_share,
        "notes": len(notes),
    }

    def no_range(label: Optional[str]) -> dict:
        return {"low": None, "high": None, "label": label, "detail": detail}

    if lead_seconds < NO_LEAD_BELOW_SECONDS:
        return no_range("no lead found")
    if pitched_share < RAPPED_BELOW_SHARE:
        return no_range("rapped")

    # Context from every lead-singing note, not only those inside lyric lines.
    around = confident & in_lead
    context = join_notes(times[around], midi_all[around], hop)
    notes, detail["octave_tops_dropped"] = drop_octave_tops(notes, context)

    counted = sorted(m for m, sec in _held(notes).items() if sec >= MIN_END_SECONDS)
    if not counted:
        return no_range(None)
    low, high = counted[0], counted[-1]
    if low == high:
        return no_range("one note")
    detail["low_moments"] = _moments(notes, low)
    detail["high_moments"] = _moments(notes, high)
    return {
        "low": midi_to_note(low),
        "high": midi_to_note(high),
        "label": None,
        "detail": detail,
    }


def measure_range(vocals_path: str, context: dict) -> dict:
    y, sr = librosa.load(vocals_path, sr=SAMPLE_RATE, mono=True)
    f0, voiced_flag, voiced_prob = librosa.pyin(
        y,
        fmin=float(librosa.note_to_hz(LOWEST_NOTE)),
        fmax=float(librosa.note_to_hz(HIGHEST_NOTE)),
        sr=sr,
        hop_length=HOP_LENGTH,
    )
    times = librosa.times_like(f0, sr=sr, hop_length=HOP_LENGTH)
    return decide_range(
        times,
        f0,
        voiced_flag,
        voiced_prob,
        HOP_LENGTH / sr,
        lead=[tuple(i) for i in context.get("lead") or []],
        lyric_lines=(
            [tuple(i) for i in context["lyric_lines"]]
            if context.get("lyric_lines")
            else None
        ),
    )


if __name__ == "__main__":
    song_context = json.loads(sys.stdin.read() or "{}")
    # stdout is the reply to the parent, not a log.
    sys.stdout.write(json.dumps(measure_range(sys.argv[1], song_context)) + "\n")
