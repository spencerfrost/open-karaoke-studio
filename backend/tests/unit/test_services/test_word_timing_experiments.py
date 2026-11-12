"""The Compare word timing page's experiments folder: moments, ordering, answers."""

import json

import pytest

from app.services import word_timing_experiments as wte

SONG = "11111111-1111-1111-1111-111111111111"
CONTROL = "22222222-2222-2222-2222-222222222222"


def word(line: int, start: float, end: float | None = None) -> dict:
    return {
        "word": "la",
        "start": start,
        "end": end or start + 0.3,
        "score": 0.5,
        "line_index": line,
    }


@pytest.fixture
def experiment(tmp_path, monkeypatch):
    monkeypatch.setattr(wte, "EXPERIMENTS_DIR", tmp_path)
    path = tmp_path / "exp"
    (path / "results").mkdir(parents=True)
    (path / "meta.json").write_text(
        json.dumps(
            {
                "name": "Test",
                "a": {"key": "lead", "label": "Lead"},
                "b": {"key": "mix", "label": "Mix"},
                "groups": [
                    {"key": "worst", "label": "W"},
                    {"key": "control", "label": "C"},
                ],
            }
        )
    )

    def write(song_id, group, lead, mix):
        (path / "results" / f"{song_id}.json").write_text(
            json.dumps(
                {
                    "id": song_id,
                    "title": song_id[:4],
                    "artist": "A",
                    "group": group,
                    "lead": {"words": lead, "bad": 1, "lines": 2, "mean_score": 0.4},
                    "mix": {"words": mix, "bad": 0, "lines": 2, "mean_score": 0.6},
                }
            )
        )

    # Line 0 the same both ways, line 1 moved by a second.
    write(
        SONG,
        "worst",
        [word(0, 1.0), word(0, 1.5), word(1, 5.0), word(1, 5.1)],
        [word(0, 1.05), word(0, 1.5), word(1, 6.0), word(1, 6.5)],
    )
    # The control sorts first by file name; its group puts it last.
    write(CONTROL, "control", [word(0, 1.0)], [word(0, 2.0)])
    return path


def test_moments_are_lines_that_moved():
    a = [word(0, 1.0), word(1, 5.0), word(2, 9.0), word(2, 9.5)]
    b = [word(0, 1.1), word(1, 6.0), word(2, 9.0)]
    found = wte.moments(a, b)
    assert [m["key"] for m in found] == ["line:1", "line:2"]
    assert found[0]["meanShift"] == 1.0
    assert found[0]["start"] == 5.0
    # A different word count always differs, with no shift to report.
    assert found[1]["meanShift"] is None


def test_moments_can_compare_ends():
    # A held word cut short: same starts, a different end.
    a = [word(0, 1.0), word(0, 1.5, 12.0)]
    b = [word(0, 1.0), word(0, 1.5, 3.0)]
    assert wte.moments(a, b) == []
    found = wte.moments(a, b, compare_ends=True)
    assert [m["key"] for m in found] == ["line:0"]
    assert found[0]["meanShift"] == 4.5
    assert found[0]["end"] == 12.0


def test_list_orders_by_group_and_counts_answers(experiment):
    listing = wte.list_songs("exp")
    assert [s["songId"] for s in listing["songs"]] == [SONG, CONTROL]
    assert listing["songs"][0]["moments"] == 1

    wte.save_answers("exp", SONG, [{"key": "line:1", "answer": "b_right"}])
    listing = wte.list_songs("exp")
    assert listing["tally"] == {"b_right": 1}
    # Fully answered songs drop below the ones still to check.
    assert [s["songId"] for s in listing["songs"]] == [CONTROL, SONG]
    assert wte.song_detail("exp", SONG)["moments"][0]["answer"] == "b_right"


def test_clearing_an_answer(experiment):
    wte.save_answers("exp", SONG, [{"key": "line:1", "answer": "a_right"}])
    wte.save_answers("exp", SONG, [{"key": "line:1", "answer": None}])
    assert wte.song_detail("exp", SONG)["moments"][0]["answer"] is None


def test_bad_answers_save_nothing(experiment):
    with pytest.raises(wte.BadAnswer):
        wte.save_answers(
            "exp",
            SONG,
            [
                {"key": "line:1", "answer": "b_right"},
                {"key": "line:0", "answer": "b_right"},
            ],
        )
    with pytest.raises(wte.BadAnswer):
        wte.save_answers("exp", SONG, [{"key": "line:1", "answer": "maybe"}])
    assert not (experiment / "answers.json").exists()


@pytest.mark.parametrize("experiment_id", ["../exp", "nope", ""])
def test_unknown_experiment(experiment, experiment_id):
    with pytest.raises(wte.NotFound):
        wte.list_songs(experiment_id)


@pytest.mark.parametrize("song_id", ["../meta", "not-a-song", "3" * 36])
def test_unknown_song(experiment, song_id):
    with pytest.raises(wte.NotFound):
        wte.song_detail("exp", song_id)


def test_no_experiments_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(wte, "EXPERIMENTS_DIR", tmp_path / "missing")
    assert wte.list_experiments() == []
