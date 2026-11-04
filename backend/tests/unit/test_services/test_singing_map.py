"""Tests for the singing map: finding sung stretches in a separated vocal stem."""

import shutil
import subprocess

import numpy as np
import pytest

from app.services.singing_map import (
    SAMPLE_RATE,
    SingingMapParams,
    measure_singing_map,
    singing_intervals,
)

RNG = np.random.default_rng(0)


def tone(seconds: float, dbfs: float) -> np.ndarray:
    """A 220 Hz sine whose RMS is `dbfs`."""
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    amplitude = np.sqrt(2) * 10 ** (dbfs / 20)
    return (amplitude * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def noise(seconds: float, dbfs: float) -> np.ndarray:
    """White noise whose RMS is `dbfs`."""
    return (RNG.standard_normal(int(seconds * SAMPLE_RATE)) * 10 ** (dbfs / 20)).astype(
        np.float32
    )


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SAMPLE_RATE), dtype=np.float32)


def assert_intervals(actual, expected, tolerance=0.05):
    assert len(actual) == len(expected), actual
    for (start, end), (want_start, want_end) in zip(actual, expected):
        assert start == pytest.approx(want_start, abs=tolerance)
        assert end == pytest.approx(want_end, abs=tolerance)


class TestSingingIntervals:
    def test_silent_stem_has_no_singing(self):
        assert singing_intervals(silence(30)) == []

    def test_empty_stem_has_no_singing(self):
        assert singing_intervals(np.zeros(0, dtype=np.float32)) == []

    def test_two_sung_stretches_with_a_gap(self):
        audio = np.concatenate([silence(5), tone(10, -20), silence(8), tone(6, -20)])
        assert_intervals(singing_intervals(audio), [(5, 15), (23, 29)])

    def test_stem_that_is_only_bleed_has_no_singing(self):
        # A backing stem on a solo song: faint noise plus a snare-like bleed,
        # all under the absolute floor.
        audio = noise(30, -60)
        audio[SAMPLE_RATE * 10 : SAMPLE_RATE * 10 + 800] += 0.004
        assert singing_intervals(audio) == []

    def test_quiet_singing_under_loud_singing_still_counts(self):
        # Verse sung softly (-30 dBFS), chorus belted (-15 dBFS). The relative
        # threshold is 15% of the chorus level, about -31.5 dBFS, so a verse
        # 15 dB under the chorus still counts. Much softer would not: that's
        # the limit of the 15% rule, to watch for on the comparison page.
        audio = np.concatenate([tone(10, -30), silence(8), tone(10, -15)])
        assert_intervals(singing_intervals(audio), [(0, 10), (18, 28)])

    def test_bleed_under_singing_is_not_singing(self):
        # Loud singing, then 10 s of bleed far below it: the bleed is above the
        # floor but under the relative threshold.
        audio = np.concatenate([tone(10, -15), noise(10, -40), tone(5, -15)])
        assert_intervals(singing_intervals(audio), [(0, 10), (20, 25)])

    def test_short_gaps_inside_a_phrase_are_joined(self):
        audio = np.concatenate([tone(2, -20), silence(0.3), tone(2, -20)])
        assert_intervals(singing_intervals(audio), [(0, 4.3)])

    def test_gap_longer_than_join_gap_splits(self):
        audio = np.concatenate([tone(2, -20), silence(1.5), tone(2, -20)])
        assert_intervals(singing_intervals(audio), [(0, 2), (3.5, 5.5)])

    def test_short_blip_is_dropped(self):
        audio = np.concatenate([silence(5), tone(0.1, -20), silence(5), tone(5, -20)])
        assert_intervals(singing_intervals(audio), [(10.1, 15.1)])

    def test_params_change_the_result(self):
        audio = np.concatenate([tone(2, -20), silence(1), tone(2, -20)])
        loose = SingingMapParams(join_gap_seconds=1.5)
        assert_intervals(singing_intervals(audio, params=loose), [(0, 5)])


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
class TestMeasureSingingMap:
    @staticmethod
    def write_mp3(path, audio):
        wav = path.with_suffix(".wav")
        import soundfile

        soundfile.write(wav, audio, SAMPLE_RATE)
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(wav),
                str(path),
            ],
            check=True,
        )
        wav.unlink()

    def test_reads_lead_and_backing_separately(self, tmp_path):
        lead = np.concatenate([silence(5), tone(10, -20), silence(10)])
        backing = np.concatenate([silence(15), tone(5, -25), silence(5)])
        self.write_mp3(tmp_path / "vocals.mp3", lead)
        self.write_mp3(tmp_path / "backing_vocals.mp3", backing)

        result = measure_singing_map(tmp_path)

        assert result["method"] == "rms"
        assert result["params"]["relative_threshold"] == 0.15
        assert result["measured_at"]
        # MP3 encoding adds a little delay, hence the wider tolerance.
        assert_intervals(result["lead"], [(5, 15)], tolerance=0.1)
        assert_intervals(result["backing"], [(15, 20)], tolerance=0.1)

    def test_no_backing_stem_reads_as_none(self, tmp_path):
        self.write_mp3(tmp_path / "vocals.mp3", tone(5, -20))
        assert measure_singing_map(tmp_path)["backing"] is None

    def test_no_lead_stem_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            measure_singing_map(tmp_path)


# ---------------------------------------------------------------------------
# Breaks from the map
# ---------------------------------------------------------------------------

from app.services.singing_map import (  # noqa: E402
    breaks_from_map,
    intersect,
    line_windows,
    subtract,
    union,
)
from app.services.singing_map_review import build_moments  # noqa: E402

# Anna Molly's layout, simplified: intro to 0:39, an ad-lib sung only by the
# backing at 1:16-1:22 with no lyric line, a bridge sung only by the backing
# at 2:12-2:38 that the lyrics have, then a real break until 2:57.
ANNA_LRC = "\n".join(
    [
        "[00:39.00] Verse one line",
        "[01:05.00] Last line before the ad-lib",
        "[01:15.00]",
        "[01:23.00] Line after the ad-lib",
        "[02:12.00] Wait, there is a light",
        "[02:30.00] Bridge line two",
        "[02:57.00] Line after the break",
        "[03:20.00] Last line",
    ]
)
ANNA_MAP = {
    "lead": [[39.0, 76.0], [83.0, 132.0], [177.0, 210.0]],
    "backing": [[76.0, 82.5], [132.0, 158.0]],
    "duration": 229.0,
}


class TestIntervalHelpers:
    def test_union_merges_overlaps_across_lists(self):
        assert union([(0, 2), (5, 6)], [(1, 3)]) == [(0, 3), (5, 6)]

    def test_intersect(self):
        assert intersect([(0, 10)], [(2, 3), (8, 12)]) == [(2, 3), (8, 10)]

    def test_subtract(self):
        assert subtract([(0, 10)], [(2, 3), (8, 12)]) == [(0, 2), (3, 8)]


class TestLineWindows:
    def test_untimed_lines_run_to_the_next_timestamp(self):
        # The last line has nothing after it: ten seconds.
        lrc = "[00:10.00] One\n[00:13.00] Two\n[00:40.00]\n[00:50.00] Three"
        windows = line_windows(lrc)
        assert [(w.index, w.start, w.end) for w in windows] == [
            (0, 10.0, 13.0),
            (1, 13.0, 40.0),
            (3, 50.0, 60.0),
        ]

    def test_word_timing_sets_a_lines_window(self):
        lrc = "[00:10.00] One two\n[00:20.00] Three"
        words = [
            {"word": "One", "start": 10.5, "end": 11.0, "line_index": 0},
            {"word": "two", "start": 11.2, "end": 12.0, "line_index": 0},
        ]
        windows = line_windows(lrc, words)
        assert (windows[0].start, windows[0].end, windows[0].timed) == (
            10.5,
            12.0,
            True,
        )
        assert windows[1].timed is False

    def test_no_lyrics(self):
        assert line_windows(None) == []


class TestBreaksFromMap:
    def test_anna_molly(self):
        breaks = breaks_from_map(ANNA_MAP, line_windows(ANNA_LRC))
        spans = [(b["start"], b["end"], b["next_line_index"]) for b in breaks]
        assert spans == [
            # The intro, leading into the first line.
            (0.0, 39.0, 0),
            # The ad-lib: backing is singing, but no line is on screen.
            (76.0, 83.0, 3),
            # Not the bridge (backing sings lines that are on screen), only
            # the real break after it.
            (158.0, 177.0, 6),
        ]
        assert all(b["source"] == "singing_map" for b in breaks)
        assert breaks[0]["lead_in_start"] == 37.5

    def test_backing_counts_as_singing_only_with_a_line_on_screen(self):
        lrc = "[00:00.00] Hello\n[00:10.00]\n[00:30.00] World"
        singing_map = {
            "lead": [[0, 5], [30, 35]],
            "backing": [[10, 20]],
            "duration": 40,
        }
        # A blank line takes "Hello" off screen at 0:10: backing after it is an ad-lib.
        breaks = breaks_from_map(singing_map, line_windows(lrc))
        assert [(b["start"], b["end"]) for b in breaks] == [(5.0, 30.0)]

    def test_short_gaps_are_not_breaks(self):
        lrc = "[00:00.00] One\n[00:10.00] Two"
        singing_map = {"lead": [[0, 5], [10, 15]], "backing": None, "duration": 20}
        assert breaks_from_map(singing_map, line_windows(lrc)) == []

    def test_silence_after_the_last_line_is_dropped(self):
        lrc = "[00:00.00] Only line"
        singing_map = {"lead": [[0, 5]], "backing": [], "duration": 60}
        assert breaks_from_map(singing_map, line_windows(lrc)) == []

    def test_no_lyrics_no_breaks(self):
        assert breaks_from_map(ANNA_MAP, []) == []


class TestMoments:
    def test_matches_breaks_and_lists_backing_only_stretches(self):
        windows = line_windows(ANNA_LRC)
        map_breaks = breaks_from_map(ANNA_MAP, windows)
        word_gaps = [
            {"start": 0.0, "end": 39.5},  # agrees with the intro
            {"start": 155.0, "end": 178.0},  # the real break, 3 s early
            {"start": 100.0, "end": 107.0},  # only the word gaps found this
        ]
        moments = build_moments(ANNA_MAP, windows, map_breaks, word_gaps)
        summary = [
            (m["kind"], m["start"], m.get("agree"), m.get("onScreen")) for m in moments
        ]
        assert summary == [
            ("break", 0.0, True, None),
            ("backing_only", 76.0, None, False),
            ("break", 76.0, False, None),  # map only
            ("break", 100.0, False, None),  # word gaps only
            ("backing_only", 132.0, None, True),
            ("break", 155.0, False, None),
        ]
        bridge = moments[4]
        assert bridge["lineText"] == "Wait, there is a light"
