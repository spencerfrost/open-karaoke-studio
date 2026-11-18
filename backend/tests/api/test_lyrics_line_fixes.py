"""Tests for /api/lyrics line fixes: a host corrects one line on the stage."""

import json
from contextlib import contextmanager
from unittest.mock import patch

from app.db.database import SessionLocal
from app.db.models import DbSong

LRC = "\n".join(
    [
        "[00:10.00]Is this the real life",
        "[00:14.00]Is this just fantasty",
        "[00:18.00]Caught in a landslide",
    ]
)
PLAIN = "Is this the real life\nIs this just fantasty\nCaught in a landslide"
WORDS = {
    "words": [
        {"word": "Is", "start": 10.0, "end": 10.3, "score": 0.9, "line_index": 0},
        {"word": "this", "start": 10.3, "end": 10.6, "score": 0.9, "line_index": 0},
        {"word": "the", "start": 10.6, "end": 10.9, "score": 0.9, "line_index": 0},
        {"word": "real", "start": 10.9, "end": 11.4, "score": 0.9, "line_index": 0},
        {"word": "life", "start": 11.4, "end": 12.0, "score": 0.9, "line_index": 0},
        {"word": "Is", "start": 14.0, "end": 14.2, "score": 0.8, "line_index": 1},
        {"word": "this", "start": 14.2, "end": 14.5, "score": 0.8, "line_index": 1},
        {"word": "just", "start": 14.5, "end": 14.9, "score": 0.8, "line_index": 1},
        {"word": "fantasty", "start": 14.9, "end": 15.8, "score": 0.1, "line_index": 1},
        {"word": "Caught", "start": 18.0, "end": 18.4, "score": 0.9, "line_index": 2},
        {"word": "in", "start": 18.4, "end": 18.5, "score": 0.9, "line_index": 2},
        {"word": "a", "start": 18.5, "end": 18.6, "score": 0.9, "line_index": 2},
        {
            "word": "landslide",
            "start": 18.6,
            "end": 19.4,
            "score": 0.9,
            "line_index": 2,
        },
    ],
    "instrumental_intervals": [],
    "language": "en",
    "mean_score": 0.8,
    "word_count": 13,
    "line_count": 3,
    "aligned_at": "2026-11-11T00:00:00+00:00",
    "lyrics_source": "lrclib:1",
}


def _song(client, *, words=True, plain=PLAIN) -> str:
    resp = client.post("/api/songs", json={"title": "Bohemian", "artist": "Queen"})
    assert resp.status_code in (200, 201)
    song_id = resp.json()["id"]
    db = SessionLocal()
    song = db.get(DbSong, song_id)
    song.synced_lyrics = LRC
    song.plain_lyrics = plain
    song.word_synced_lyrics = json.dumps(WORDS) if words else None
    db.commit()
    db.close()
    return song_id


def _stored(song_id: str) -> DbSong:
    db = SessionLocal()
    song = db.get(DbSong, song_id)
    db.expunge(song)
    db.close()
    return song


@contextmanager
def _vocals(exist=True):
    """Vocals on disk (or not), and the Celery send captured."""
    with patch("app.services.file_service.FileService.get_vocals_path") as path, patch(
        "app.jobs.celery_app.celery.send_task"
    ) as send:
        path.return_value.exists.return_value = exist
        send.return_value.id = "task-1"
        yield send


def _fix(client, song_id, *, line_start=14.0, old="Is this just fantasty", new):
    return client.post(
        f"/api/lyrics/songs/{song_id}/line-fixes",
        json={"line_start": line_start, "old_text": old, "new_text": new},
    )


def test_a_fix_replaces_the_line_and_times_only_that_line(client):
    song_id = _song(client)

    with _vocals() as send:
        resp = _fix(client, song_id, new="Is this just  fantasy ")

    assert resp.status_code == 200
    body = resp.json()
    assert body["lineIndex"] == 1
    assert body["text"] == "Is this just fantasy"
    fix = body["fix"]
    assert fix["oldText"] == "Is this just fantasty"
    assert fix["newText"] == "Is this just fantasy"
    assert fix["fixedBy"] == "testuser"
    assert fix["alignStatus"] == "pending"
    assert fix["shown"] is True

    song = _stored(song_id)
    assert "[00:14.00]Is this just fantasy" in song.synced_lyrics.splitlines()
    assert song.plain_lyrics.splitlines()[1] == "Is this just fantasy"
    # Not hand-picked: that path re-aligns the whole song.
    assert song.lyrics_hand_picked_at is None
    # The line's new words sit on its old timing until they are timed again.
    words = json.loads(song.word_synced_lyrics)["words"]
    assert [w["line_index"] for w in words] == [0] * 5 + [1] * 4 + [2] * 4
    line = [w for w in words if w["line_index"] == 1]
    assert [w["word"] for w in line] == ["Is", "this", "just", "fantasy"]
    assert [(w["start"], w["end"]) for w in line] == [
        (14.0, 14.2),
        (14.2, 14.5),
        (14.5, 14.9),
        (14.9, 15.8),
    ]

    send.assert_called_once()
    assert send.call_args.args[0] == "align_lyrics_line"
    assert send.call_args.kwargs["args"] == [
        song_id,
        1,
        "Is this just fantasy",
        WORDS["aligned_at"],
    ]
    assert send.call_args.kwargs["kwargs"] == {"fix_id": fix["id"]}
    assert send.call_args.kwargs["queue"] == "lyrics"


def test_a_song_without_word_timing_is_fixed_but_not_timed(client):
    song_id = _song(client, words=False)

    with _vocals() as send:
        resp = _fix(client, song_id, new="Is this just fantasy")

    assert resp.json()["fix"]["alignStatus"] == "no_timing"
    send.assert_not_called()


def test_no_vocals_means_no_timing_run_and_the_line_keeps_its_timing(client):
    song_id = _song(client)

    with _vocals(exist=False) as send:
        resp = _fix(client, song_id, new="Is this just fantasy")

    assert resp.json()["fix"]["alignStatus"] == "no_timing"
    send.assert_not_called()
    words = json.loads(_stored(song_id).word_synced_lyrics)["words"]
    assert [w["word"] for w in words if w["line_index"] == 1][-1] == "fantasy"


def test_a_fix_to_punctuation_or_case_keeps_the_words_timing(client):
    song_id = _song(client)

    with _vocals() as send:
        resp = _fix(client, song_id, new="Is this just, FANTASTY?")

    assert resp.json()["fix"]["alignStatus"] == "aligned"
    send.assert_not_called()
    words = json.loads(_stored(song_id).word_synced_lyrics)["words"]
    line = [w for w in words if w["line_index"] == 1]
    assert [w["word"] for w in line] == ["Is", "this", "just,", "FANTASTY?"]
    assert [w["score"] for w in line] == [0.8, 0.8, 0.8, 0.1]


def test_a_fix_with_more_words_shares_the_lines_old_span(client):
    song_id = _song(client)

    with _vocals():
        _fix(client, song_id, new="Is this just a fan to see")

    payload = json.loads(_stored(song_id).word_synced_lyrics)
    line = [w for w in payload["words"] if w["line_index"] == 1]
    assert len(line) == 7
    assert (line[0]["start"], line[-1]["end"]) == (14.0, 15.8)
    # Only the intro is a break: none appears where the line is sung.
    assert [i["end"] for i in payload["instrumental_intervals"]] == [10.0]


def test_a_lost_fix_isnt_taken_for_another_line_that_reads_its_words(client):
    song_id = _song(client)
    with _vocals():
        lost = _fix(client, song_id, new="Is this just fantasy").json()["fix"]
    db = SessionLocal()
    song = db.get(DbSong, song_id)
    # New lyrics without the fixed line; another line happens to read its words.
    song.synced_lyrics = (
        "[00:40.00]Mama\n[00:44.00]Is this just fantasy\n[00:48.00]Oooh"
    )
    song.plain_lyrics = None
    song.word_synced_lyrics = None
    db.commit()
    db.close()

    with _vocals():
        fix = _fix(
            client,
            song_id,
            line_start=44.0,
            old="Is this just fantasy",
            new="Is this just a fantasy",
        ).json()["fix"]

    assert fix["id"] != lost["id"]
    assert fix["oldText"] == "Is this just fantasy"


def test_a_line_that_changed_since_it_was_shown_is_refused(client):
    song_id = _song(client)

    with _vocals():
        moved = _fix(client, song_id, line_start=15.0, new="Is this just fantasy")
        reworded = _fix(client, song_id, old="Something else", new="x")

    assert moved.status_code == 409
    assert reworded.status_code == 409


def test_text_that_isnt_a_fix_is_refused(client):
    song_id = _song(client)

    with _vocals():
        same = _fix(client, song_id, new="Is this just fantasty")
        empty = _fix(client, song_id, new="   ")
        two_lines = _fix(client, song_id, new="one\ntwo")

    assert same.status_code == 422
    assert empty.status_code == 422
    assert two_lines.status_code == 422


def test_fixing_a_fixed_line_again_keeps_one_fix_with_its_first_text(client):
    song_id = _song(client)

    with _vocals():
        first = _fix(client, song_id, new="Is this just fantasy?").json()["fix"]
        second = _fix(
            client, song_id, old="Is this just fantasy?", new="Is this just fantasy"
        ).json()["fix"]

    assert second["id"] == first["id"]
    assert second["oldText"] == "Is this just fantasty"
    assert second["newText"] == "Is this just fantasy"
    assert len(client.get(f"/api/lyrics/songs/{song_id}/line-fixes").json()) == 1


def test_typing_the_first_text_back_removes_the_fix(client):
    song_id = _song(client)

    with _vocals():
        _fix(client, song_id, new="Is this just fantasy")
        resp = _fix(
            client, song_id, old="Is this just fantasy", new="Is this just fantasty"
        )

    assert resp.status_code == 200
    assert resp.json()["fix"] is None
    assert client.get(f"/api/lyrics/songs/{song_id}/line-fixes").json() == []
    assert "[00:14.00]Is this just fantasty" in _stored(song_id).synced_lyrics


def test_undo_puts_the_first_text_back_and_times_the_line(client):
    song_id = _song(client)
    with _vocals():
        fix = _fix(client, song_id, new="Is this just fantasy").json()["fix"]

    with _vocals() as send:
        resp = client.delete(f"/api/lyrics/line-fixes/{fix['id']}")

    assert resp.status_code == 200
    assert resp.json() == {"restored": True, "songId": song_id}
    song = _stored(song_id)
    assert "[00:14.00]Is this just fantasty" in song.synced_lyrics.splitlines()
    assert song.plain_lyrics.splitlines()[1] == "Is this just fantasty"
    assert send.call_args.kwargs["args"][:3] == [song_id, 1, "Is this just fantasty"]
    assert client.get(f"/api/lyrics/songs/{song_id}/line-fixes").json() == []
    assert client.delete(f"/api/lyrics/line-fixes/{fix['id']}").status_code == 404


def test_a_fix_whose_line_is_gone_is_listed_as_lost_and_undo_only_removes_it(
    client,
):
    song_id = _song(client)
    with _vocals():
        fix = _fix(client, song_id, new="Is this just fantasy").json()["fix"]

    db = SessionLocal()
    song = db.get(DbSong, song_id)
    song.synced_lyrics = "[00:05.00]Completely different lyrics"
    db.commit()
    db.close()

    listed = client.get(f"/api/lyrics/songs/{song_id}/line-fixes").json()
    assert listed[0]["shown"] is False
    lost = [entry for entry in client.get("/api/lyrics/line-fixes/lost").json()]
    assert any(
        entry["id"] == fix["id"] and entry["songTitle"] == "Bohemian" for entry in lost
    )

    with _vocals() as send:
        resp = client.delete(f"/api/lyrics/line-fixes/{fix['id']}")
    assert resp.json()["restored"] is False
    send.assert_not_called()
    assert _stored(song_id).synced_lyrics == "[00:05.00]Completely different lyrics"


def test_a_song_with_only_plain_lyrics_cant_take_a_line_fix(client):
    song_id = _song(client)
    db = SessionLocal()
    db.get(DbSong, song_id).synced_lyrics = None
    db.commit()
    db.close()

    with _vocals():
        resp = _fix(client, song_id, new="Is this just fantasy")
    assert resp.status_code == 422


def test_line_fixes_on_a_missing_song_are_404(client):
    assert client.get("/api/lyrics/songs/nope/line-fixes").status_code == 404
    with _vocals():
        assert _fix(client, "nope", new="x").status_code == 404
