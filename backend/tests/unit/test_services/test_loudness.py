"""Tests for loudness measurement: the gain formula, ffmpeg output parsing, and a real ffmpeg run."""

import shutil
import subprocess

import pytest

from app.services.audio import (
    LoudnessResult,
    compute_normalization_gain,
    detect_loudness,
    parse_loudnorm_output,
)

LOUDNORM_STDERR = """Input #0, mp3, from 'instrumental.mp3':
  Duration: 00:03:21.12, start: 0.025057, bitrate: 192 kb/s
[Parsed_loudnorm_0 @ 0x55d0c8a1c2c0]
{
\t"input_i" : "-9.84",
\t"input_tp" : "0.31",
\t"input_lra" : "5.20",
\t"input_thresh" : "-19.93",
\t"output_i" : "-24.02",
\t"output_tp" : "-13.75",
\t"output_lra" : "4.60",
\t"output_thresh" : "-34.08",
\t"normalization_type" : "dynamic",
\t"target_offset" : "0.02"
}
[out#0/null @ 0x55d0c8a1d980] video:0KiB audio:34650KiB
"""


class TestComputeNormalizationGain:
    def test_loud_song_is_turned_down_to_target(self):
        assert compute_normalization_gain(-9.8, 0.3) == pytest.approx(-6.2)

    def test_quiet_song_is_boosted_to_target(self):
        assert compute_normalization_gain(-20.0, -8.0) == pytest.approx(4.0)

    def test_boost_stops_before_the_peak_passes_the_ceiling(self):
        # Target wants +6 dB, but the peak is only 3 dB under the -1 dBTP ceiling.
        assert compute_normalization_gain(-22.0, -4.0) == pytest.approx(3.0)

    def test_peak_already_over_the_ceiling_is_turned_down(self):
        # At target loudness, but a +0.5 dBTP peak still needs a cut.
        assert compute_normalization_gain(-16.0, 0.5) == pytest.approx(-1.5)

    def test_absurd_measurements_are_limited(self):
        assert compute_normalization_gain(-60.0, -50.0) == pytest.approx(12.0)
        assert compute_normalization_gain(5.0, 0.0) == pytest.approx(-12.0)


class TestParseLoudnormOutput:
    def test_reads_loudness_and_true_peak(self):
        assert parse_loudnorm_output(LOUDNORM_STDERR) == (-9.84, 0.31)

    def test_silence_reads_as_none(self):
        silent = LOUDNORM_STDERR.replace('"-9.84"', '"-inf"').replace(
            '"0.31"', '"-inf"'
        )
        assert parse_loudnorm_output(silent) is None

    def test_near_silence_reads_as_none(self):
        assert (
            parse_loudnorm_output(LOUDNORM_STDERR.replace('"-9.84"', '"-72.00"'))
            is None
        )

    def test_missing_summary_raises(self):
        with pytest.raises(ValueError):
            parse_loudnorm_output("Error opening input file instrumental.mp3")


class TestDetectLoudness:
    def test_missing_instrumental_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            detect_loudness(tmp_path)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
class TestDetectLoudnessWithFfmpeg:
    @staticmethod
    def _tone(path, volume_db):
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1000:duration=5",
                "-af",
                f"volume={volume_db}dB",
                str(path),
            ],
            check=True,
        )

    def test_measures_the_instrumental(self, tmp_path):
        self._tone(tmp_path / "instrumental.mp3", 2)

        result = detect_loudness(tmp_path)

        assert isinstance(result, LoudnessResult)
        assert -21.0 < result.loudness_lufs < -18.0
        assert result.gain_db == pytest.approx(
            compute_normalization_gain(result.loudness_lufs, result.true_peak_dbtp)
        )

    def test_sums_backing_vocals_at_full_level(self, tmp_path):
        self._tone(tmp_path / "instrumental.mp3", 2)
        alone = detect_loudness(tmp_path)
        self._tone(tmp_path / "backing_vocals.mp3", 2)

        summed = detect_loudness(tmp_path)

        # Two identical stems summed at full level read 6 dB louder. amix's
        # default scaling would read the same as one stem.
        assert summed.loudness_lufs - alone.loudness_lufs == pytest.approx(6.0, abs=0.3)

    def test_silent_stem_reads_as_none(self, tmp_path):
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=44100:cl=stereo",
                "-t",
                "3",
                str(tmp_path / "instrumental.mp3"),
            ],
            check=True,
        )

        assert detect_loudness(tmp_path) is None
