"""The Check vocal range page's results folder: moments, verdicts, answers."""

import json

import numpy as np
import pytest

from app.services import vocal_range_review as vrr

SUNG = "11111111-1111-1111-1111-111111111111"
RAPPED = "test-thumbnail-auto"  # test songs aren't all uuids


def _song(song_id, group):
    return {
        "song_id": song_id,
        "title": song_id[:4],
        "artist": "A",
        "picked_as": group,
        "stored_low": "G3",
        "stored_high": "A6",
    }


def _run(method, results):
    return {"method": method, "setting": "pyin", "results": results}


def _result(low, high, low_at, high_at):
    return {
        "low": low,
        "high": high,
        "label": None,
        "low_moments": [{"start": t, "duration": 0.3} for t in low_at],
        "high_moments": [{"start": t, "duration": 0.3} for t in high_at],
    }


@pytest.fixture
def results(tmp_path, monkeypatch):
    folder = tmp_path / "results"
    (folder / "runs").mkdir(parents=True)
    monkeypatch.setattr(vrr, "RESULTS_DIR", folder)
    (folder / "testset.json").write_text(
        json.dumps({"songs": [_song(SUNG, "wide"), _song(RAPPED, "named")]})
    )
    # Both methods agree on the low moment; "notes" moves the high one.
    (folder / "runs" / "baseline.json").write_text(
        json.dumps(
            _run(
                "baseline",
                {
                    SUNG: _result("G3", "A6", [10.0], [50.0, 60.0]),
                    RAPPED: _result("C3", "C4", [5.0], [7.0]),
                },
            )
        )
    )
    (folder / "runs" / "notes.json").write_text(
        json.dumps(_run("notes", {SUNG: _result("G3", "A4", [10.0], [30.0])}))
    )
    (tmp_path / "reference.json").write_text(
        json.dumps({"_about": "x", RAPPED: {"kind": "rapped"}})
    )
    return folder


def test_moments_are_shared_across_methods(results):
    song = vrr.song_detail(SUNG)

    assert [m["key"] for m in song["moments"]] == [
        "G3@10.00",
        "A4@30.00",  # rank 0 for "notes"
        "A6@50.00",  # rank 0 for baseline
        "A6@60.00",
    ]
    low = song["moments"][0]
    assert [s["method"] for s in low["sets"]] == ["baseline", "notes"]
    assert [m["method"] for m in song["methods"]] == ["baseline", "notes"]


def test_contour_excerpt_keeps_voiced_frames_around_the_moment(results):
    contours = results / "contours" / "pyin"
    contours.mkdir(parents=True)
    times = np.arange(0, 20, 0.5, dtype=np.float32)
    f0 = np.full(times.shape, 196.0, dtype=np.float32)  # G3
    f0[times == 10.5] = np.nan
    prob = np.where(times == 11.0, 0.2, 0.9).astype(np.float32)
    np.savez(contours / f"{SUNG}.npz", times=times, f0=f0, voiced_prob=prob)

    excerpt = vrr.song_detail(SUNG)["moments"][0]["contour"]

    assert excerpt["start"] == 8.0 and excerpt["end"] == 12.3
    assert [p[0] for p in excerpt["points"]] == [
        8.0,
        8.5,
        9.0,
        9.5,
        10.0,
        11.0,
        11.5,
        12.0,
    ]
    assert excerpt["points"][0][1] == pytest.approx(55.0, abs=0.01)
    assert [p[2] for p in excerpt["points"]][5] == 0  # low probability: faint


def test_answers_and_verdicts(results):
    vrr.save_answers(
        SUNG,
        [
            {"key": "G3@10.00", "answer": "right"},
            {"key": "A6@50.00", "answer": "cant_tell"},
            {"key": "A6@60.00", "answer": "octave_high"},
            {"key": "kind", "answer": "sung"},
        ],
    )

    song = vrr.song_detail(SUNG)
    by_method = {m["method"]: m["verdicts"] for m in song["methods"]}
    # "Can't tell" passes the verdict to the end's next moment.
    assert by_method["baseline"] == {"low": "right", "high": "octave_high"}
    assert by_method["notes"] == {"low": "right", "high": None}
    assert song["kind"] == "sung"

    listing = vrr.list_songs()
    assert listing["verdicts"]["baseline"] == {"right": 1, "octave_high": 1}
    assert listing["kinds"] == {"sung": 1}
    row = next(r for r in listing["songs"] if r["songId"] == SUNG)
    # Only primary moments count: A6@60.00 is baseline's backup.
    assert (row["moments"], row["answered"]) == (3, 2)


def test_moments_know_whether_they_decide_an_end(results):
    primary = {m["key"]: m["primary"] for m in vrr.song_detail(SUNG)["moments"]}
    assert primary == {
        "G3@10.00": True,
        "A4@30.00": True,
        "A6@50.00": True,
        "A6@60.00": False,
    }


def test_methods_narrow_the_moments(results):
    song = vrr.song_detail(SUNG, ["notes"])
    assert [m["method"] for m in song["methods"]] == ["notes"]
    assert [m["key"] for m in song["moments"]] == ["G3@10.00", "A4@30.00"]

    listing = vrr.list_songs(["notes"])
    assert [m["method"] for m in listing["methods"]] == ["notes"]
    assert [m["method"] for m in listing["allMethods"]] == ["baseline", "notes"]
    row = next(r for r in listing["songs"] if r["songId"] == SUNG)
    assert row["moments"] == 2


def test_clearing_an_answer(results):
    vrr.save_answers(SUNG, [{"key": "G3@10.00", "answer": "right"}])
    vrr.save_answers(SUNG, [{"key": "G3@10.00", "answer": None}])

    assert vrr.song_detail(SUNG)["moments"][0]["answer"] is None


@pytest.mark.parametrize(
    "item",
    [
        {"key": "C2@1.00", "answer": "right"},
        {"key": "G3@10.00", "answer": "sung"},
        {"key": "kind", "answer": "right"},
    ],
)
def test_bad_answers_save_nothing(results, item):
    with pytest.raises(vrr.BadAnswer):
        vrr.save_answers(SUNG, [{"key": "G3@10.00", "answer": "right"}, item])

    assert not (results / "answers.json").exists()


def test_unknown_song(results):
    with pytest.raises(vrr.NotFound):
        vrr.song_detail("nope")


def test_finished_songs_go_last_then_by_group(results):
    listing = vrr.list_songs()
    assert [r["songId"] for r in listing["songs"]] == [RAPPED, SUNG]
    assert listing["songs"][0]["referenceKind"] == "rapped"

    vrr.save_answers(
        RAPPED,
        [
            {"key": "C3@5.00", "answer": "not_singer"},
            {"key": "C4@7.00", "answer": "not_singer"},
            {"key": "kind", "answer": "rapped"},
        ],
    )
    assert [r["songId"] for r in vrr.list_songs()["songs"]] == [SUNG, RAPPED]


def test_no_results_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(vrr, "RESULTS_DIR", tmp_path / "missing")
    assert vrr.list_songs()["songs"] == []


@pytest.mark.parametrize("answer", ["no_note", "screamed"])
def test_moments_without_a_clear_note(results, answer):
    vrr.save_answers(SUNG, [{"key": "G3@10.00", "answer": answer}])

    song = vrr.song_detail(SUNG)
    assert song["moments"][0]["answer"] == answer
    assert song["methods"][0]["verdicts"]["low"] == answer
