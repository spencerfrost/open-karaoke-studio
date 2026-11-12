import sys
from types import SimpleNamespace

import numpy as np
import pytest

from app.services import lyrics_offset
from app.services.lyrics_analysis import parse_lrc_lines
from app.services.lyrics_offset import (
    _fine_shifts,
    _sweep_shifts,
    pick_best_lrc_shift,
    shift_lrc_timestamps,
    sweep_lrc_offset,
)

# ---------------------------------------------------------------------------
# pick_best_lrc_shift
# ---------------------------------------------------------------------------


def test_pick_best_lrc_shift_reports_the_highest_scoring_shift_and_its_gain():
    sweep = pick_best_lrc_shift({-1.0: 0.30, 0.0: 0.25, 1.0: 0.60, 1.5: 0.55})

    assert sweep["shift"] == 1.0
    assert sweep["score"] == 0.6
    assert sweep["baseline_score"] == 0.25
    assert sweep["gain"] == 0.35


def test_pick_best_lrc_shift_breaks_ties_toward_the_smaller_shift():
    """An LRC that is already right must not drift just because a shifted copy scores the same."""
    sweep = pick_best_lrc_shift({-0.5: 0.4, 0.0: 0.4, 0.5: 0.4})

    assert sweep["shift"] == 0.0
    assert sweep["gain"] == 0.0


def test_sweep_shifts_is_symmetric_and_includes_zero():
    shifts = _sweep_shifts(12.0, 0.5)

    assert len(shifts) == 49
    assert shifts[0] == -12.0
    assert shifts[-1] == 12.0
    assert 0.0 in shifts


def test_fine_shifts_fill_the_gaps_either_side_of_the_coarse_best():
    assert _fine_shifts(-1.0, 0.5, 0.1, 1.5) == [
        -1.4,
        -1.3,
        -1.2,
        -1.1,
        -0.9,
        -0.8,
        -0.7,
        -0.6,
    ]


def test_fine_shifts_stay_within_the_sweep():
    assert _fine_shifts(1.5, 0.5, 0.1, 1.5) == [1.1, 1.2, 1.3, 1.4]


# ---------------------------------------------------------------------------
# sweep_lrc_offset — direction contract, with WhisperX faked
# ---------------------------------------------------------------------------

TRUE_VOCAL_STARTS = [10.0, 14.0, 18.0, 22.0]


def _fake_whisperx():
    """
    Scores each segment by how close its window start is to where that line
    is really sung — the property the sweep relies on: windows that land on
    the vocals align with high confidence.
    """

    def align(
        segments, _model, _metadata, _audio, _device, return_char_alignments=False
    ):
        out = []
        for segment, true_start in zip(segments, TRUE_VOCAL_STARTS):
            score = max(0.0, 1.0 - abs(segment["start"] - true_start) / 4.0)
            out.append(
                {
                    "words": [
                        {"word": w, "score": score} for w in segment["text"].split()
                    ]
                }
            )
        return {"segments": out}

    return SimpleNamespace(load_align_model=lambda **_kwargs: (None, None), align=align)


@pytest.fixture
def fake_alignment(monkeypatch):
    monkeypatch.setitem(sys.modules, "whisperx", _fake_whisperx())
    monkeypatch.setattr(
        lyrics_offset,
        "load_sung_vocals",
        lambda _path: (np.zeros(16000, dtype=np.float32), 16000),
    )


@pytest.mark.parametrize("lrc_error", [-6.0, -2.5, 1.5, 4.0, 9.0])
def test_sweep_returns_the_shift_that_puts_the_lyrics_back_on_the_vocals(
    fake_alignment, tmp_path, lrc_error
):
    """
    Regression for the old estimator, which reported (vocals - LRC) and then
    applied it negated, pushing late lyrics even later. The sweep's `shift`
    is the correction itself: applying it as-is must land on the vocals.
    """
    lrc = "\n".join(
        f"[00:{start + lrc_error:05.2f}]line number {i}"
        for i, start in enumerate(TRUE_VOCAL_STARTS)
    )

    sweep = sweep_lrc_offset(lrc, tmp_path / "vocals.mp3", device="cpu")

    assert sweep is not None
    assert sweep["shift"] == -lrc_error
    assert sweep["score"] == 1.0
    assert sweep["gain"] > 0.0
    corrected_starts = [
        line["timestamp"]
        for line in parse_lrc_lines(shift_lrc_timestamps(lrc, sweep["shift"]))
    ]
    assert corrected_starts == pytest.approx(TRUE_VOCAL_STARTS)


def test_sweep_leaves_correctly_timed_lyrics_alone(fake_alignment, tmp_path):
    lrc = "\n".join(
        f"[00:{start:05.2f}]line number {i}"
        for i, start in enumerate(TRUE_VOCAL_STARTS)
    )

    sweep = sweep_lrc_offset(lrc, tmp_path / "vocals.mp3", device="cpu")

    assert sweep is not None
    assert sweep["shift"] == 0.0
    assert sweep["gain"] == 0.0


def test_sweep_returns_none_when_there_are_no_lyric_lines(fake_alignment, tmp_path):
    assert (
        sweep_lrc_offset(
            "[00:05.00]\n[00:09.00]", tmp_path / "vocals.mp3", device="cpu"
        )
        is None
    )


@pytest.mark.parametrize("lrc_error", [0.9, -0.3, 0.2, 1.4])
def test_fine_sweep_finds_offsets_between_coarse_steps(
    fake_alignment, tmp_path, lrc_error
):
    """GRiZ "Find My Own Way" is 0.9 s late: the coarse 0.5 s steps land
    either side of it and the fine pass finds it."""
    lrc = "\n".join(
        f"[00:{start + lrc_error:05.2f}]line number {i}"
        for i, start in enumerate(TRUE_VOCAL_STARTS)
    )

    sweep = sweep_lrc_offset(
        lrc,
        tmp_path / "vocals.mp3",
        device="cpu",
        max_shift=1.5,
        step=0.5,
        fine_step=0.1,
    )

    assert sweep is not None
    assert sweep["shift"] == pytest.approx(-lrc_error)
    assert sweep["score"] == 1.0
    # 7 coarse shifts and 8 fine ones, minus any fine shift past the edge.
    assert 11 <= len(sweep["scores"]) <= 15


def test_sweep_without_a_fine_step_only_tries_coarse_shifts(fake_alignment, tmp_path):
    lrc = "\n".join(
        f"[00:{start + 0.9:05.2f}]line number {i}"
        for i, start in enumerate(TRUE_VOCAL_STARTS)
    )

    sweep = sweep_lrc_offset(
        lrc, tmp_path / "vocals.mp3", device="cpu", max_shift=1.5, step=0.5
    )

    assert sweep is not None
    assert set(sweep["scores"]) == {-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5}
    assert sweep["shift"] == -1.0


def test_fine_shifts_out_to_a_reach_shorter_than_the_step():
    assert _fine_shifts(4.0, 1.0, 0.1, 12.0, reach=0.5) == [
        3.5,
        3.6,
        3.7,
        3.8,
        3.9,
        4.1,
        4.2,
        4.3,
        4.4,
        4.5,
    ]


@pytest.mark.parametrize("lrc_error", [-4.6, 2.3])
def test_wide_sweep_in_whole_seconds_finds_an_offset_of_seconds(
    fake_alignment, tmp_path, lrc_error
):
    """Gretchen Wilson "Redneck Woman": the LRC is 4.6 s early, a whole line."""
    lrc = "\n".join(
        f"[00:{start + lrc_error:05.2f}]line number {i}"
        for i, start in enumerate(TRUE_VOCAL_STARTS)
    )

    sweep = sweep_lrc_offset(
        lrc,
        tmp_path / "vocals.mp3",
        device="cpu",
        max_shift=12.0,
        step=1.0,
        fine_step=0.1,
        fine_reach=0.5,
        fine_around_zero=False,
    )

    assert sweep is not None
    assert sweep["shift"] == pytest.approx(-lrc_error)
    # 25 coarse shifts and 10 fine ones.
    assert len(sweep["scores"]) == 35


def test_wide_sweep_skips_the_fine_pass_when_no_shift_wins(fake_alignment, tmp_path):
    lrc = "\n".join(
        f"[00:{start:05.2f}]line number {i}"
        for i, start in enumerate(TRUE_VOCAL_STARTS)
    )

    sweep = sweep_lrc_offset(
        lrc,
        tmp_path / "vocals.mp3",
        device="cpu",
        max_shift=12.0,
        step=1.0,
        fine_step=0.1,
        fine_reach=0.5,
        fine_around_zero=False,
    )

    assert sweep is not None
    assert sweep["shift"] == 0.0
    assert len(sweep["scores"]) == 25
