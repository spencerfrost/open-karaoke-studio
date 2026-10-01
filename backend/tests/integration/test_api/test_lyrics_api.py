"""Integration tests for DB-backed /api/lyrics endpoints."""

import uuid
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from app.api.dependencies import RequesterContext, require_host_or_session_member
from app.db.models import DbSong
from tests.integration.conftest import _TestingSessionLocal


def _create_song(client, title="Lyric Song", artist="Lyrical Artist"):
    resp = client.post("/api/songs", json={"title": title, "artist": artist})
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/lyrics/songs/{song_id}
# ─────────────────────────────────────────────────────────────────────────────


def test_get_song_lyrics_song_not_found(client):
    resp = client.get(f"/api/lyrics/songs/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_get_song_lyrics_empty(client):
    song_id = _create_song(client)
    resp = client.get(f"/api/lyrics/songs/{song_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plainLyrics"] is None
    assert data["syncedLyrics"] is None
    assert data["hasAlignment"] is False


def test_get_song_lyrics_after_update(client):
    song_id = _create_song(client)
    client.post(
        f"/api/lyrics/songs/{song_id}?type=plain",
        json={"content": "Hello world"},
    )
    resp = client.get(f"/api/lyrics/songs/{song_id}")
    assert resp.status_code == 200
    assert resp.json()["plainLyrics"] == "Hello world"


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/lyrics/songs/{song_id}
# ─────────────────────────────────────────────────────────────────────────────


def test_update_lyrics_song_not_found(client):
    resp = client.post(
        f"/api/lyrics/songs/{uuid.uuid4()}?type=plain",
        json={"content": "Test"},
    )
    assert resp.status_code == 404


def test_update_lyrics_invalid_type(client):
    song_id = _create_song(client)
    resp = client.post(
        f"/api/lyrics/songs/{song_id}?type=word_synced",
        json={"content": "Test"},
    )
    assert resp.status_code == 400


def test_update_plain_lyrics_success(client):
    song_id = _create_song(client)
    resp = client.post(
        f"/api/lyrics/songs/{song_id}?type=plain",
        json={"content": "Plain lyrics here"},
    )
    assert resp.status_code == 200
    assert resp.json()["plainLyrics"] == "Plain lyrics here"


def test_update_plain_lyrics_clears_alignment(client):
    song_id = _create_song(client)
    with _TestingSessionLocal() as session:
        song = session.get(DbSong, song_id)
        song.word_synced_lyrics = '{"words": [{"word": "hello"}]}'
        session.commit()

    resp = client.post(
        f"/api/lyrics/songs/{song_id}?type=plain",
        json={"content": "Updated plain lyrics"},
    )

    assert resp.status_code == 200
    data = client.get(f"/api/lyrics/songs/{song_id}").json()
    assert data["hasAlignment"] is False


def test_update_synced_lyrics_success(client):
    song_id = _create_song(client)
    resp = client.post(
        f"/api/lyrics/songs/{song_id}?type=synced",
        json={"content": "[00:00.00] Line 1"},
    )
    assert resp.status_code == 200
    assert resp.json()["syncedLyrics"] == "[00:00.00] Line 1"


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/lyrics/songs/{song_id}/{type}
# ─────────────────────────────────────────────────────────────────────────────


def test_clear_lyrics_song_not_found(client):
    resp = client.delete(f"/api/lyrics/songs/{uuid.uuid4()}/plain")
    assert resp.status_code == 404


def test_clear_lyrics_invalid_type(client):
    song_id = _create_song(client)
    resp = client.delete(f"/api/lyrics/songs/{song_id}/invalid")
    assert resp.status_code == 400


def test_clear_plain_lyrics_success(client):
    song_id = _create_song(client)
    client.post(f"/api/lyrics/songs/{song_id}?type=plain", json={"content": "Delete me"})
    resp = client.delete(f"/api/lyrics/songs/{song_id}/plain")
    assert resp.status_code == 204
    data = client.get(f"/api/lyrics/songs/{song_id}").json()
    assert data["plainLyrics"] is None


def test_clear_plain_lyrics_clears_alignment(client):
    song_id = _create_song(client)
    client.post(f"/api/lyrics/songs/{song_id}?type=plain", json={"content": "Delete me"})
    with _TestingSessionLocal() as session:
        song = session.get(DbSong, song_id)
        song.word_synced_lyrics = '{"words": [{"word": "hello"}]}'
        session.commit()

    resp = client.delete(f"/api/lyrics/songs/{song_id}/plain")

    assert resp.status_code == 204
    data = client.get(f"/api/lyrics/songs/{song_id}").json()
    assert data["hasAlignment"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Removed endpoints — verify they no longer exist
# ─────────────────────────────────────────────────────────────────────────────


def test_activate_endpoint_gone(client):
    resp = client.patch("/api/lyrics/999999/activate")
    assert resp.status_code == 404


def test_delete_by_id_endpoint_gone(client):
    resp = client.delete("/api/lyrics/999999")
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Lyrics reports
# ─────────────────────────────────────────────────────────────────────────────


@contextmanager
def _as_guest(client, name="Sam"):
    """Make requests as a guest's phone in a session, not an account."""
    app = client.app
    previous = app.dependency_overrides[require_host_or_session_member]
    guest = SimpleNamespace(display_name=name, device_type="performer", session_id=None)
    app.dependency_overrides[require_host_or_session_member] = lambda: RequesterContext(
        device=guest
    )
    try:
        yield
    finally:
        app.dependency_overrides[require_host_or_session_member] = previous


def _song_with_lyrics(
    client, *, synced="[00:01.00]Blackbird singing", hand_picked=False
):
    from datetime import datetime, timezone

    song_id = _create_song(client, title="Blackbird", artist="The Beatles")
    db = _TestingSessionLocal()
    song = db.get(DbSong, song_id)
    song.synced_lyrics = synced
    song.lyrics_hand_picked_at = datetime.now(timezone.utc) if hand_picked else None
    db.commit()
    db.close()
    return song_id


@contextmanager
def _vocals_ready():
    with patch("app.api.lyrics.FileService") as mock_files, patch(
        "app.api.lyrics.enqueue_song_alignment", return_value={"dispatched": True}
    ) as mock_enqueue:
        mock_files.return_value.get_vocals_path.return_value.exists.return_value = True
        yield mock_enqueue


def test_a_guest_reports_wrong_words_and_a_fix_is_queued(client):
    song_id = _song_with_lyrics(client)

    with _as_guest(client), _vocals_ready() as mock_enqueue:
        resp = client.post(
            f"/api/lyrics/songs/{song_id}/reports", json={"kind": "words"}
        )

    assert resp.status_code == 200
    report = resp.json()["report"]
    assert report["kind"] == "words"
    assert report["reportCount"] == 1
    assert report["reporterName"] == "Sam"
    assert report["outcome"] is None
    mock_enqueue.assert_called_once()
    assert mock_enqueue.call_args.kwargs["include_remote"] is True


def test_reporting_the_same_lyrics_again_counts_on_one_report(client):
    song_id = _song_with_lyrics(client)

    with _as_guest(client, "Sam"), _vocals_ready():
        client.post(f"/api/lyrics/songs/{song_id}/reports", json={"kind": "words"})
    with _as_guest(client, "Alex"), _vocals_ready():
        resp = client.post(
            f"/api/lyrics/songs/{song_id}/reports", json={"kind": "words"}
        )

    assert resp.json()["report"]["reportCount"] == 2
    assert resp.json()["report"]["reporterName"] == "Alex"
    assert len(client.get("/api/lyrics/reports").json()) == 1


def test_wrong_words_unlocks_hand_picked_lyrics_but_out_of_sync_doesnt(client):
    timing_song = _song_with_lyrics(client, hand_picked=True)
    words_song = _song_with_lyrics(client, hand_picked=True)

    with _as_guest(client), _vocals_ready():
        client.post(f"/api/lyrics/songs/{timing_song}/reports", json={"kind": "timing"})
        client.post(f"/api/lyrics/songs/{words_song}/reports", json={"kind": "words"})

    assert client.get(f"/api/songs/{timing_song}").json()["lyricsHandPicked"] is True
    assert client.get(f"/api/songs/{words_song}").json()["lyricsHandPicked"] is False


def test_a_song_without_lyrics_cant_be_reported(client):
    song_id = _create_song(client)

    with _as_guest(client), _vocals_ready() as mock_enqueue:
        resp = client.post(
            f"/api/lyrics/songs/{song_id}/reports", json={"kind": "words"}
        )

    assert resp.status_code == 422
    mock_enqueue.assert_not_called()


def test_only_known_report_kinds_are_accepted(client):
    song_id = _song_with_lyrics(client)

    with _as_guest(client), _vocals_ready():
        resp = client.post(
            f"/api/lyrics/songs/{song_id}/reports", json={"kind": "bad vibes"}
        )

    assert resp.status_code == 422


def test_resolving_a_report_takes_it_off_the_list(client):
    song_id = _song_with_lyrics(client)
    with _as_guest(client), _vocals_ready():
        report_id = client.post(
            f"/api/lyrics/songs/{song_id}/reports", json={"kind": "timing"}
        ).json()["report"]["id"]

    assert [report["id"] for report in client.get("/api/lyrics/reports").json()] == [
        report_id
    ]

    resp = client.post(f"/api/lyrics/reports/{report_id}/resolve")

    assert resp.status_code == 200
    assert resp.json()["resolved"] is True
    assert client.get("/api/lyrics/reports").json() == []
    assert client.post("/api/lyrics/reports/999999/resolve").status_code == 404
