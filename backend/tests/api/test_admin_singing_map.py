"""Tests for the Compare breaks endpoints: the song list and one song."""

import json
from unittest.mock import patch

from app.db.models import DbSong

LRC = "[00:10.00] First line\n[00:30.00] Second line"
MAP = {
    "method": "rms",
    "lead": [[10.0, 15.0], [30.0, 35.0]],
    "backing": [],
    "duration": 40.0,
}
# Today's breaks: the intro only. The map also finds 0:15-0:30.
WORDS = {
    "words": [
        {"word": "First", "start": 10.0, "end": 10.5, "score": 0.9, "line_index": 0},
        {"word": "Second", "start": 30.0, "end": 30.5, "score": 0.9, "line_index": 1},
    ],
    "instrumental_intervals": [
        {
            "start": 0.0,
            "end": 10.0,
            "duration": 10.0,
            "lead_in_start": 8.5,
            "next_line_index": 0,
            "confidence": 1.0,
            "source": "whisperx_gap",
        }
    ],
}


def _add(db, song_id, title, **fields):
    db.add(DbSong(id=song_id, title=title, artist="Band", status="processed", **fields))
    db.commit()


class TestListSingingMapSongs:
    def test_lists_songs_with_synced_lyrics_most_disagreement_first(self, client, db):
        _add(
            db,
            "differs",
            "B song",
            synced_lyrics=LRC,
            word_synced_lyrics=json.dumps(WORDS),
            singing_map=json.dumps(MAP),
        )
        _add(db, "unmeasured", "A song", synced_lyrics=LRC)
        _add(db, "no-lyrics", "C song", singing_map=json.dumps(MAP))

        resp = client.get("/api/admin/singing-map/songs")

        assert resp.status_code == 200
        rows = resp.json()["songs"]
        assert [r["songId"] for r in rows] == ["differs", "unmeasured"]
        assert rows[0] == {
            "songId": "differs",
            "title": "B song",
            "artist": "Band",
            "measured": True,
            "hasWordTiming": True,
            "wordGapBreaks": 1,
            "mapBreaks": 2,
            "disagreements": 1,
            "toCheck": 1,
            "answers": [],
        }
        assert rows[1]["measured"] is False
        assert rows[1]["disagreements"] is None


class TestGetSingingMapSong:
    def test_returns_breaks_and_moments(self, client, db):
        _add(
            db,
            "song",
            "Song",
            synced_lyrics=LRC,
            word_synced_lyrics=json.dumps(WORDS),
            singing_map=json.dumps(MAP),
        )

        resp = client.get("/api/admin/singing-map/songs/song")

        assert resp.status_code == 200
        body = resp.json()
        assert body["duration"] == 40.0
        assert [(b["start"], b["end"]) for b in body["mapBreaks"]] == [
            (0.0, 10.0),
            (15.0, 30.0),
        ]
        assert [(m["kind"], m["agree"]) for m in body["moments"]] == [
            ("break", True),
            ("break", False),
        ]
        assert body["moments"][1]["wordGaps"] is None
        assert [line["timed"] for line in body["lines"]] == [True, True]

    def test_song_without_vocals_track(self, client, db):
        _add(db, "song", "Song", synced_lyrics=LRC)
        with patch(
            "app.jobs.metadata_tasks.detect_and_store_singing_map",
            return_value="no_audio",
        ):
            resp = client.get("/api/admin/singing-map/songs/song")
        assert resp.status_code == 409

    def test_unknown_song(self, client):
        assert client.get("/api/admin/singing-map/songs/nope").status_code == 404


def _add_differs(db):
    _add(
        db,
        "song",
        "Song",
        synced_lyrics=LRC,
        word_synced_lyrics=json.dumps(WORDS),
        singing_map=json.dumps(MAP),
    )


def _moments(client):
    return client.get("/api/admin/singing-map/songs/song").json()["moments"]


class TestSaveSingingMapChecks:
    def test_answer_shows_on_the_moment_and_in_the_list(self, client, db):
        _add_differs(db)
        map_only = _moments(client)[1]
        assert map_only["key"] == "break:15.00-30.00:-"
        assert map_only["answer"] is None

        resp = client.put(
            "/api/admin/singing-map/songs/song/checks",
            json={"answers": [{"key": map_only["key"], "answer": "map_right"}]},
        )

        assert resp.status_code == 200
        assert resp.json()["moments"][1]["answer"] == "map_right"
        listing = client.get("/api/admin/singing-map/songs").json()
        assert listing["songs"][0]["toCheck"] == 0
        assert listing["songs"][0]["answers"] == ["map_right"]
        assert listing["tally"] == {"map_right": 1}

    def test_changing_and_clearing_an_answer(self, client, db):
        _add_differs(db)
        key = _moments(client)[1]["key"]
        url = "/api/admin/singing-map/songs/song/checks"
        client.put(url, json={"answers": [{"key": key, "answer": "map_right"}]})
        client.put(url, json={"answers": [{"key": key, "answer": "both_wrong"}]})
        assert _moments(client)[1]["answer"] == "both_wrong"

        client.put(url, json={"answers": [{"key": key, "answer": None}]})
        assert _moments(client)[1]["answer"] is None

    def test_a_moved_moment_needs_a_fresh_answer(self, client, db):
        _add_differs(db)
        key = _moments(client)[1]["key"]
        client.put(
            "/api/admin/singing-map/songs/song/checks",
            json={"answers": [{"key": key, "answer": "map_right"}]},
        )
        song = db.get(DbSong, "song")
        song.singing_map = json.dumps({**MAP, "lead": [[10.0, 16.0], [30.0, 35.0]]})
        db.commit()

        moved = _moments(client)[1]
        assert moved["key"] == "break:16.00-30.00:-"
        assert moved["answer"] is None

    def test_rejects_an_answer_that_doesnt_fit(self, client, db):
        _add_differs(db)
        key = _moments(client)[1]["key"]
        resp = client.put(
            "/api/admin/singing-map/songs/song/checks",
            json={
                "answers": [
                    {"key": key, "answer": "map_right"},
                    {"key": key, "answer": "bar_fine"},
                ]
            },
        )
        assert resp.status_code == 400
        assert _moments(client)[1]["answer"] is None

    def test_rejects_a_moment_the_song_no_longer_shows(self, client, db):
        _add_differs(db)
        resp = client.put(
            "/api/admin/singing-map/songs/song/checks",
            json={"answers": [{"key": "break:1.00-9.00:-", "answer": "map_right"}]},
        )
        assert resp.status_code == 400
