"""Range methods: a cached contour (plus the song's context) in, a range out.

Each method returns a RangeResult with the two notes and the moments that set
them, so the ear-check page can play exactly what decided each end. Add a
method by writing a function and registering it in METHODS with the contour
setting it reads.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

import numpy as np
from common import Contour, TestSong, inside, midi_to_note

# The production numbers, from app/services/vocal_range_child.py.
MIN_VOICED_PROBABILITY = 0.75
MIN_CONFIDENT_FRAMES = 10
LOW_PERCENTILE = 5
HIGH_PERCENTILE = 95

# Moments: frames of one note this close together are one moment.
MOMENT_JOIN_SECONDS = 0.1
MOMENTS_PER_END = 3


@dataclass
class Moment:
    start: float
    duration: float


@dataclass
class RangeResult:
    low: Optional[str]
    high: Optional[str]
    low_moments: list[Moment] = field(default_factory=list)
    high_moments: list[Moment] = field(default_factory=list)
    # None for a sung range; otherwise why there is no range ("rapped", ...).
    label: Optional[str] = None
    # Anything a method wants to report for the scorer (counts, shares).
    detail: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return asdict(self)


def note_moments(
    times: np.ndarray, rounded_midi: np.ndarray, note: int, hop: float
) -> list[Moment]:
    """The longest runs of frames at `note`, longest first.

    A percentile interpolates between frames, so it can land on a note no frame
    sits at; the frames nearest to it stand in.
    """
    if rounded_midi.size == 0:
        return []
    distance = np.abs(rounded_midi - note)
    at = times[distance == distance.min()]
    runs: list[list[float]] = [[float(at[0]), float(at[0])]]
    for t in at[1:]:
        if t - runs[-1][1] <= MOMENT_JOIN_SECONDS:
            runs[-1][1] = float(t)
        else:
            runs.append([float(t), float(t)])
    moments = [Moment(round(a, 2), round(b - a + hop, 2)) for a, b in runs]
    moments.sort(key=lambda m: m.duration, reverse=True)
    return moments[:MOMENTS_PER_END]


def confident_mask(
    contour: Contour, min_probability: float = MIN_VOICED_PROBABILITY
) -> np.ndarray:
    return (
        contour.voiced_flag
        & (contour.voiced_prob > min_probability)
        & ~np.isnan(contour.f0)
    )


def frame_percentiles(contour: Contour, song: TestSong) -> RangeResult:
    """Today's method: 5th/95th percentile over confident pyin frames."""
    mask = confident_mask(contour)
    if mask.sum() < MIN_CONFIDENT_FRAMES:
        return RangeResult(None, None, detail={"confident_frames": int(mask.sum())})
    midi = contour.midi[mask]
    times = contour.times[mask]
    low = round(float(np.percentile(midi, LOW_PERCENTILE)))
    high = round(float(np.percentile(midi, HIGH_PERCENTILE)))
    rounded = np.round(midi).astype(int)
    return RangeResult(
        low=midi_to_note(low),
        high=midi_to_note(high),
        low_moments=note_moments(times, rounded, low, contour.hop_seconds),
        high_moments=note_moments(times, rounded, high, contour.hop_seconds),
        detail={"confident_frames": int(mask.sum())},
    )


# --- Notes, not frames -------------------------------------------------------

# Frames join one note while each stays this close (semitones) to the note so far.
NOTE_TOLERANCE = 0.5
# A gap of up to this many unvoiced frames doesn't end a note.
NOTE_MAX_GAP_FRAMES = 2
# A note must be held at least this long to count...
MIN_NOTE_SECONDS = 0.15
# ...and an end of the range must be sung for at least this long in total.
MIN_END_SECONDS = 0.25
# Octave cleanup: median window (frames), and a jump this big from both
# neighbours drops a frame.
MEDIAN_FRAMES = 5
OCTAVE_JUMP = 10
# A looser voiced-probability cut: pyin rarely passes 0.75 on separated stems
# (1-36% of lead-singing frames on the test songs), so the strict cut decides
# a range from a few seconds of singing.
LOOSE_PROBABILITY = 0.3
# Labels. Pitched share: lead-singing frames pyin is fairly sure are pitched
# (above PITCHED_PROBABILITY). Rap and speech sat at 1-9% on the test songs,
# sung songs at 16% and up.
PITCHED_PROBABILITY = 0.5
RAPPED_BELOW_SHARE = 0.10
# Less lead singing than this (s): the lead stem holds no singer to measure.
NO_LEAD_BELOW_SECONDS = 10.0
# From the ear answers (2026-11-10): no cut separates rap cleanly; 0.07 called
# two treated sung voices rapped and missed two raps.
RAPPED_BELOW_SHARE_V2 = 0.07
# Octave context: a top note held an octave above the highest note sung within
# CONTEXT_SECONDS of it, and well above their median, is pyin reading it an
# octave up. By ear it caught 3 of 7 octave errors and none of 12 right tops.
CONTEXT_SECONDS = 4.0
OCTAVE_ABOVE_NEAREST = (11, 13)
OCTAVE_ABOVE_MEDIAN = 13


@dataclass
class Note:
    start: float
    end: float
    midi: int


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


def drop_octave_tops(
    notes: list[Note], context: list[Note], detail: dict
) -> list[Note]:
    """Drop top notes that read an octave up, until the top one doesn't."""
    dropped = 0
    while True:
        held: dict[int, float] = {}
        for note in notes:
            held[note.midi] = held.get(note.midi, 0.0) + note.end - note.start
        counted = [m for m, sec in held.items() if sec >= MIN_END_SECONDS]
        if not counted:
            break
        top = max(counted)
        bad = [n for n in notes if n.midi == top and octave_up(n, context)]
        if not bad:
            break
        notes = [n for n in notes if n not in bad]
        dropped += len(bad)
    detail["octave_tops_dropped"] = dropped
    return notes


def range_from_notes(
    notes: list[Note], detail: dict, one_note_is_none: bool = False
) -> RangeResult:
    """Lowest and highest note sung for MIN_END_SECONDS in total."""
    held: dict[int, float] = {}
    for note in notes:
        held[note.midi] = held.get(note.midi, 0.0) + note.end - note.start
    counted = sorted(m for m, seconds in held.items() if seconds >= MIN_END_SECONDS)
    if not counted:
        return RangeResult(None, None, detail=detail)
    low, high = counted[0], counted[-1]
    if one_note_is_none and low == high:
        return RangeResult(None, None, label="one note", detail=detail)

    def moments(pitch: int) -> list[Moment]:
        at = sorted(
            (n for n in notes if n.midi == pitch),
            key=lambda n: n.end - n.start,
            reverse=True,
        )
        return [
            Moment(round(n.start, 2), round(n.end - n.start, 2))
            for n in at[:MOMENTS_PER_END]
        ]

    return RangeResult(
        low=midi_to_note(low),
        high=midi_to_note(high),
        low_moments=moments(low),
        high_moments=moments(high),
        detail=detail,
    )


def octave_cleanup(midi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Median-filtered pitches, and a mask of frames that survive the jump rule."""
    keep = np.ones(midi.size, dtype=bool)
    if midi.size >= 3:
        prev_jump = np.abs(midi[1:-1] - midi[:-2]) >= OCTAVE_JUMP
        next_jump = np.abs(midi[1:-1] - midi[2:]) >= OCTAVE_JUMP
        keep[1:-1] = ~(prev_jump & next_jump)
    half = MEDIAN_FRAMES // 2
    padded = np.pad(midi, half, mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, MEDIAN_FRAMES)
    return np.median(windows, axis=1), keep


def _notes_method(
    contour: Contour,
    song: TestSong,
    *,
    gate_lead: bool,
    gate_lyrics: bool,
    cleanup: bool,
    min_probability: float = MIN_VOICED_PROBABILITY,
    labels: bool = False,
    rapped_below: float = RAPPED_BELOW_SHARE,
    octave_context: bool = False,
    one_note_is_none: bool = False,
) -> RangeResult:
    mask = confident_mask(contour, min_probability)
    detail: dict = {"min_probability": min_probability}
    gates: list[str] = []
    if gate_lead:
        if song["lead_intervals"] is not None:
            mask &= inside(contour.times, song["lead_intervals"])
            gates.append("lead")
        else:
            detail["no_singing_map"] = True
    if gate_lyrics:
        if song["lyric_lines"]:
            mask &= inside(contour.times, song["lyric_lines"])
            gates.append("lyrics")
        else:
            detail["no_lyric_lines"] = True
    detail["gates"] = gates

    times = contour.times[mask]
    midi = contour.midi[mask]
    if cleanup and midi.size:
        smoothed, keep = octave_cleanup(midi)
        detail["octave_dropped"] = int((~keep).sum())
        times, midi = times[keep], smoothed[keep]

    hop = contour.hop_seconds
    notes = join_notes(times, midi, hop)
    voiced_seconds = float(times.size * hop)
    note_seconds = sum(n.end - n.start for n in notes)
    lead_seconds = (
        sum(b - a for a, b in song["lead_intervals"])
        if song["lead_intervals"] is not None
        else None
    )
    detail.update(
        voiced_seconds=round(voiced_seconds, 1),
        note_seconds=round(note_seconds, 1),
        # Rap and speech glide; singing holds pitches. For step 5's labels.
        stable_share=(
            round(note_seconds / voiced_seconds, 3) if voiced_seconds else None
        ),
        lead_seconds=round(lead_seconds, 1) if lead_seconds is not None else None,
        notes=len(notes),
    )
    if song["lead_intervals"] is not None:
        lead = inside(contour.times, song["lead_intervals"])
        pitched = lead & confident_mask(contour, PITCHED_PROBABILITY)
        detail["pitched_share"] = (
            round(float(pitched.sum() / lead.sum()), 3) if lead.any() else 0.0
        )
    if labels and lead_seconds is not None:
        if lead_seconds < NO_LEAD_BELOW_SECONDS:
            return RangeResult(None, None, label="no lead found", detail=detail)
        if detail["pitched_share"] < rapped_below:
            return RangeResult(None, None, label="rapped", detail=detail)
    if octave_context:
        # Context from every lead-singing note, not only the gated ones.
        around = confident_mask(contour, min_probability)
        if song["lead_intervals"] is not None:
            around &= inside(contour.times, song["lead_intervals"])
        context = join_notes(contour.times[around], contour.midi[around], hop)
        notes = drop_octave_tops(notes, context, detail)
    return range_from_notes(notes, detail, one_note_is_none)


def notes(contour: Contour, song: TestSong) -> RangeResult:
    """Held notes (≥150 ms, steady within ½ semitone); ends need ≥0.25 s in total."""
    return _notes_method(
        contour, song, gate_lead=False, gate_lyrics=False, cleanup=False
    )


def notes_lead(contour: Contour, song: TestSong) -> RangeResult:
    """Held notes, only while the singing map says the lead is singing."""
    return _notes_method(
        contour, song, gate_lead=True, gate_lyrics=False, cleanup=False
    )


def notes_lyrics(contour: Contour, song: TestSong) -> RangeResult:
    """Held notes, only while the lead sings and a lyric line is on screen."""
    return _notes_method(contour, song, gate_lead=True, gate_lyrics=True, cleanup=False)


def notes_lead_octave(contour: Contour, song: TestSong) -> RangeResult:
    """Held notes while the lead sings, after a median filter and the octave-jump rule."""
    return _notes_method(contour, song, gate_lead=True, gate_lyrics=False, cleanup=True)


def notes_lead_loose(contour: Contour, song: TestSong) -> RangeResult:
    """Held notes while the lead sings, keeping frames pyin is only 30% sure of."""
    return _notes_method(
        contour,
        song,
        gate_lead=True,
        gate_lyrics=False,
        cleanup=False,
        min_probability=LOOSE_PROBABILITY,
    )


def notes_lead_labels(contour: Contour, song: TestSong) -> RangeResult:
    """notes+lead, labelling rapped songs and leads with no singer instead."""
    return _notes_method(
        contour, song, gate_lead=True, gate_lyrics=False, cleanup=False, labels=True
    )


def notes_lead_c6(contour: Contour, song: TestSong) -> RangeResult:
    """notes+lead+labels on a pyin run capped at C6 (fmax) instead of C7."""
    return notes_lead_labels(contour, song)


def lyrics_v2(contour: Contour, song: TestSong) -> RangeResult:
    """notes+lyrics, labelled (rap below 7%), octave-up tops dropped, one note is no range."""
    return _notes_method(
        contour,
        song,
        gate_lead=True,
        gate_lyrics=True,
        cleanup=False,
        labels=True,
        rapped_below=RAPPED_BELOW_SHARE_V2,
        octave_context=True,
        one_note_is_none=True,
    )


Method = Callable[[Contour, TestSong], RangeResult]

# name -> (contour setting, function)
METHODS: dict[str, tuple[str, Method]] = {
    "baseline": ("pyin", frame_percentiles),
    "notes": ("pyin", notes),
    "notes+lead": ("pyin", notes_lead),
    "notes+lyrics": ("pyin", notes_lyrics),
    "lyrics-v2": ("pyin", lyrics_v2),
    "notes+lead+octave": ("pyin", notes_lead_octave),
    "notes+lead+loose": ("pyin", notes_lead_loose),
    "notes+lead+labels": ("pyin", notes_lead_labels),
    "notes+lead+labels+c6": ("pyin-c6", notes_lead_c6),
}
