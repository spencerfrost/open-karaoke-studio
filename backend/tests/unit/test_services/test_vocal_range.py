"""Tests for vocal range detection: the method in vocal_range_child.py, and
detect_vocal_range, which runs it in a child process."""

import importlib.util
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from app.services import audio
from app.services.audio import VocalRangeContext, detect_vocal_range
from app.services.vocal_range import lyric_line_windows

SAMPLE_RATE = 22050
HOP = 512 / SAMPLE_RATE

# The child is run by path, never imported by the app; load it the same way.
_spec = importlib.util.spec_from_file_location(
    "vocal_range_child", audio._VOCAL_RANGE_CHILD
)
assert _spec is not None and _spec.loader is not None
child = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(child)


def _midi_to_hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _track(notes: list[tuple[float, float, float]], seconds: float = 60.0, prob=0.9):
    """A pitch track holding each (start, end, midi) note, unvoiced elsewhere."""
    times = np.arange(int(seconds / HOP)) * HOP
    f0 = np.full(times.shape, np.nan)
    for start, end, midi in notes:
        f0[(times >= start) & (times < end)] = _midi_to_hz(midi)
    voiced = ~np.isnan(f0)
    probability = np.where(voiced, prob, 0.0)
    return times, f0, voiced, probability


def _decide(track, lead=((0.0, 12.0),), lyric_lines=None):
    """The method on `track`; by default the lead sings its first 12 s."""
    times, f0, voiced, probability = track
    return child.decide_range(
        times, f0, voiced, probability, HOP, list(lead), lyric_lines
    )


class TestDecideRange:
    def test_lowest_and_highest_held_notes(self):
        # A3 (57) and E4 (64) held a second each, a passing D4 too short to count.
        result = _decide(_track([(1, 2, 57), (3, 3.1, 62), (5, 6, 64)]))

        assert (result["low"], result["high"], result["label"]) == ("A3", "E4", None)
        assert result["detail"]["method"] == "lyrics-v2"
        assert result["detail"]["high_moments"][0]["start"] == pytest.approx(5, abs=HOP)

    def test_only_while_the_lead_sings(self):
        # The C6 at 30 s is outside the lead's intervals: backing bleed, say.
        track = _track([(1, 2, 57), (5, 6, 64), (30, 31, 84)])

        result = _decide(track, lead=[(0.0, 20.0)])

        assert result["high"] == "E4"

    def test_only_while_a_lyric_line_is_on_screen(self):
        track = _track([(1, 2, 57), (5, 6, 64), (15, 16, 69)])

        result = _decide(track, lead=[(0.0, 20.0)], lyric_lines=[(0.0, 10.0)])

        assert result["high"] == "E4"
        assert result["detail"]["gates"] == ["lead", "lyrics"]

    def test_a_top_note_an_octave_up_is_dropped(self):
        # Sung around A3–C4; pyin reads one held note at C5, an octave above.
        track = _track([(1, 2, 57), (3, 4, 60), (4.2, 5, 72), (5.2, 6, 59)])

        result = _decide(track)

        assert result["high"] == "C4"
        assert result["detail"]["octave_tops_dropped"] == 1

    def test_rarely_pitched_lead_is_rapped(self):
        # The lead "sings" for 60 s but pyin hears pitch for one second of it.
        result = _decide(_track([(1, 2, 57)]), lead=[(0.0, 60.0)])

        assert (result["low"], result["high"]) == (None, None)
        assert result["label"] == "rapped"

    def test_no_lead_found(self):
        result = _decide(_track([(1, 2, 57), (3, 4, 64)]), lead=[(0.0, 5.0)])

        assert result["label"] == "no lead found"

    def test_one_note_is_no_range(self):
        result = _decide(_track([(1, 10, 57), (11, 20, 57)]), lead=[(0.0, 30.0)])

        assert (result["low"], result["label"]) == (None, "one note")


class TestLyricLineWindows:
    def test_each_line_until_the_next_capped(self):
        lrc = "[00:01.00]One\n[00:03.00]\n[00:04.00]Two\n[00:30.00]Three\n"

        assert lyric_line_windows(lrc, duration=35.0) == [
            (1.0, 4.0),
            (4.0, 14.0),
            (30.0, 35.0),
        ]

    def test_out_of_order_timestamps_are_sorted(self):
        lrc = "[00:10.00]Two\n[00:02.00]One\n"

        assert lyric_line_windows(lrc, duration=None) == [(2.0, 10.0), (10.0, 20.0)]

    def test_no_synced_lyrics(self):
        assert lyric_line_windows(None, 100.0) is None


def _write_tones(path: Path, frequencies: list[float], seconds_each: float):
    """A clean sine per frequency, back to back: pyin reads it as sung notes."""
    t = np.arange(int(SAMPLE_RATE * seconds_each)) / SAMPLE_RATE
    wave = np.concatenate([0.5 * np.sin(2 * np.pi * f * t) for f in frequencies])
    sf.write(path, wave.astype(np.float32), SAMPLE_RATE)


def _completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


WHOLE_SONG = VocalRangeContext(lead=[(0.0, 12.0)], lyric_lines=None)


class TestDetectVocalRangeEndToEnd:
    def test_reads_lowest_and_highest_note(self, tmp_path):
        vocals = tmp_path / "vocals.wav"
        # A3 and E4, six seconds each: past the ten seconds of lead a range needs.
        _write_tones(vocals, [220.0, 329.63], seconds_each=6.0)

        result = detect_vocal_range(vocals, WHOLE_SONG, lambda _msg: None)

        assert (result["low"], result["high"], result["label"]) == ("A3", "E4", None)

    def test_silence_has_no_range(self, tmp_path):
        vocals = tmp_path / "vocals.wav"
        sf.write(vocals, np.zeros(SAMPLE_RATE * 12, dtype=np.float32), SAMPLE_RATE)

        result = detect_vocal_range(vocals, WHOLE_SONG, lambda _msg: None)

        assert (result["low"], result["high"]) == (None, None)
        assert result["label"] == "rapped"

    def test_unreadable_file_raises(self, tmp_path):
        """A failure is not "no range": the caller must be able to tell them apart."""
        vocals = tmp_path / "vocals.mp3"
        vocals.write_bytes(b"not audio")

        with pytest.raises(RuntimeError, match="vocal range analysis failed"):
            detect_vocal_range(vocals, WHOLE_SONG, lambda _msg: None)


REPLY = {"low": "G2", "high": "E5", "label": None, "detail": {"method": "lyrics-v2"}}


class TestVocalRangeChildFailures:
    """The child's failures raise with the reason, through detect_vocal_range."""

    @pytest.fixture
    def run(self):
        with patch.object(audio.subprocess, "run") as run:
            yield run

    def test_runs_the_child_isolated_with_a_timeout(self, run, tmp_path):
        run.return_value = _completed(json.dumps(REPLY) + "\n")

        assert detect_vocal_range(tmp_path / "v.mp3", WHOLE_SONG, lambda _m: None) == (
            REPLY
        )
        command = run.call_args.args[0]
        assert command[1] == "-I"
        assert command[2].endswith("vocal_range_child.py")
        assert run.call_args.kwargs["timeout"] == audio._VOCAL_RANGE_TIMEOUT_SECONDS
        assert json.loads(run.call_args.kwargs["input"]) == {
            "lead": [[0.0, 12.0]],
            "lyric_lines": None,
        }

    def test_reply_after_other_output_is_still_read(self, run, tmp_path):
        run.return_value = _completed("stray line\n" + json.dumps(REPLY) + "\n")

        assert detect_vocal_range(tmp_path / "v.mp3", WHOLE_SONG, lambda _m: None) == (
            REPLY
        )

    def test_any_failure_raises(self, run, tmp_path):
        run.return_value = _completed(stderr="boom", returncode=1)

        with pytest.raises(RuntimeError, match="boom"):
            detect_vocal_range(tmp_path / "v.mp3", WHOLE_SONG, lambda _m: None)

    def test_timeout(self, run, tmp_path):
        run.side_effect = subprocess.TimeoutExpired(cmd="child", timeout=600)

        with pytest.raises(RuntimeError, match="took over 600s"):
            audio._run_vocal_range_child(tmp_path / "v.mp3", WHOLE_SONG)

    def test_child_crash(self, run, tmp_path):
        run.return_value = _completed(stderr="Segmentation fault", returncode=-11)

        with pytest.raises(RuntimeError, match=r"failed \(-11\): Segmentation fault"):
            audio._run_vocal_range_child(tmp_path / "v.mp3", WHOLE_SONG)

    @pytest.mark.parametrize(
        "stdout",
        [
            "",
            "not json",
            '{"low": "C3"}',
            "[1, 2]",
            '{"low": null, "high": null, "label": null, "detail": 3}',
        ],
    )
    def test_unreadable_reply(self, run, tmp_path, stdout):
        run.return_value = _completed(stdout)

        with pytest.raises(RuntimeError, match="unreadable reply"):
            audio._run_vocal_range_child(tmp_path / "v.mp3", WHOLE_SONG)
