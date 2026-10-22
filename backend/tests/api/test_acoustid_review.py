"""Tests for the AcoustID review actions: accept a suggestion, keep the current
names, apply a picked recording, and how a person's edit confirms a song."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from app.db.models import DbSong

SONG_ID = "song-acoustid"


@pytest.fixture
def mock_celery():
    with patch("app.jobs.celery_app.celery") as celery:
        celery.send_task.return_value = Mock(id="task-1")
        yield celery


def _add_song(db, **fields):
    values = {
        "id": SONG_ID,
        "title": "Stick Season",
        "artist": "Walk off the Earth",
        "acoustid_fingerprint_status": "suggested",
        "acoustid_score": 1.0,
        "acoustid_suggested_recording_id": "mbid-kidz",
        "acoustid_suggested_title": "Stick Season",
        "acoustid_suggested_artist": "Kidz Bop",
        **fields,
    }
    db.add(DbSong(**values))
    db.commit()


def _fetch(db):
    db.expire_all()
    return db.get(DbSong, SONG_ID)


class TestAcceptSuggestion:
    def test_renames_links_and_confirms(self, client, db, mock_celery):
        _add_song(db)

        resp = client.post(f"/api/songs/{SONG_ID}/fingerprint/suggestion/accept")

        assert resp.status_code == 200
        song = _fetch(db)
        assert song.artist == "Kidz Bop"
        assert song.musicbrainz_recording_id == "mbid-kidz"
        assert song.acoustid_fingerprint_status == "matched"
        assert song.acoustid_suggested_recording_id is None
        assert song.metadata_confirmed_at is not None
        mock_celery.send_task.assert_called_once_with(
            "enrich_song_artist_credits", args=[SONG_ID], kwargs={"picked": True}
        )

    def test_without_a_suggestion_is_409(self, client, db, mock_celery):
        _add_song(
            db,
            acoustid_fingerprint_status="matched",
            acoustid_suggested_recording_id=None,
        )

        resp = client.post(f"/api/songs/{SONG_ID}/fingerprint/suggestion/accept")

        assert resp.status_code == 409
        mock_celery.send_task.assert_not_called()

    def test_unknown_song_is_404(self, client, mock_celery):
        resp = client.post("/api/songs/nope/fingerprint/suggestion/accept")
        assert resp.status_code == 404


class TestKeepCurrent:
    def test_keeps_the_names_and_confirms(self, client, db):
        _add_song(db)

        resp = client.post(f"/api/songs/{SONG_ID}/skip-fingerprint")

        assert resp.status_code == 200
        song = _fetch(db)
        assert song.artist == "Walk off the Earth"
        assert song.acoustid_fingerprint_status == "skipped"
        assert song.acoustid_suggested_recording_id is None
        assert song.metadata_confirmed_at is not None

    def test_keeps_a_matched_songs_recording(self, client, db):
        _add_song(
            db,
            acoustid_fingerprint_status="ambiguous",
            acoustid_suggested_recording_id=None,
            musicbrainz_recording_id="mbid-kept",
        )

        client.post(f"/api/songs/{SONG_ID}/skip-fingerprint")

        assert _fetch(db).musicbrainz_recording_id == "mbid-kept"


class TestApplyPickedRecording:
    def test_confirms_and_clears_the_suggestion(self, client, db, mock_celery):
        _add_song(db)

        resp = client.post(
            f"/api/songs/{SONG_ID}/fingerprint/apply",
            json={
                "recording_id": "mbid-wote",
                "title": "Stick Season",
                "artist": "Walk off the Earth",
                "score": 0.95,
            },
        )

        assert resp.status_code == 200
        song = _fetch(db)
        assert song.musicbrainz_recording_id == "mbid-wote"
        assert song.acoustid_suggested_recording_id is None
        assert song.metadata_confirmed_at is not None


class TestEditConfirms:
    def test_changing_the_artist_confirms_and_drops_the_recording(self, client, db):
        _add_song(
            db,
            acoustid_fingerprint_status="matched",
            acoustid_suggested_recording_id=None,
            musicbrainz_recording_id="mbid-old",
        )

        resp = client.patch(f"/api/songs/{SONG_ID}", json={"artist": "Noah Kahan"})

        assert resp.status_code == 200
        song = _fetch(db)
        assert song.metadata_confirmed_at is not None
        assert song.musicbrainz_recording_id is None
        assert song.acoustid_fingerprint_status == "skipped"
        assert resp.json()["metadataConfirmed"] is True

    def test_resending_the_same_names_changes_nothing(self, client, db):
        _add_song(
            db,
            acoustid_fingerprint_status="matched",
            acoustid_suggested_recording_id=None,
            musicbrainz_recording_id="mbid-old",
        )

        client.patch(
            f"/api/songs/{SONG_ID}",
            json={"title": "Stick Season", "artist": "Walk off the Earth"},
        )

        song = _fetch(db)
        assert song.metadata_confirmed_at is None
        assert song.musicbrainz_recording_id == "mbid-old"

    def test_editing_other_fields_does_not_confirm(self, client, db):
        _add_song(db)

        client.patch(f"/api/songs/{SONG_ID}", json={"album": "Stick Season"})

        song = _fetch(db)
        assert song.metadata_confirmed_at is None
        assert song.acoustid_suggested_recording_id == "mbid-kidz"

    def test_a_song_still_waiting_for_a_fingerprint_keeps_waiting(self, client, db):
        _add_song(
            db,
            acoustid_fingerprint_status="not_checked",
            acoustid_suggested_recording_id=None,
        )

        client.patch(f"/api/songs/{SONG_ID}", json={"title": "Stick Season (Live)"})

        assert _fetch(db).acoustid_fingerprint_status == "not_checked"


class TestSuggestionInResponses:
    def test_suggested_songs_list_with_their_suggestion(self, client, db):
        _add_song(db, metadata_confirmed_at=None)

        resp = client.get("/api/songs/by-fingerprint-status?status=suggested")

        assert resp.status_code == 200
        [song] = resp.json()
        assert song["acoustidSuggestion"] == {
            "recordingId": "mbid-kidz",
            "title": "Stick Season",
            "artist": "Kidz Bop",
        }
        assert song["metadataConfirmed"] is False

    def test_confirmed_flag(self, client, db):
        _add_song(
            db,
            acoustid_fingerprint_status="skipped",
            acoustid_suggested_recording_id=None,
            metadata_confirmed_at=datetime(2026, 10, 1),
        )

        resp = client.get("/api/songs/by-fingerprint-status?status=skipped")

        [song] = resp.json()
        assert song["acoustidSuggestion"] is None
        assert song["metadataConfirmed"] is True
