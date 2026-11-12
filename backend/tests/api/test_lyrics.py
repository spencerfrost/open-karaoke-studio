"""Tests for /api/lyrics: LRCLIB search, per-song lyrics, reports and alignment runs."""

import uuid
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from app.api.dependencies import RequesterContext, require_host_or_session_member
from app.db.database import SessionLocal
from app.db.models import DbSong


class TestLyricsSearch:
    """Tests for lyrics search endpoint."""

    def test_search_returns_results(self, client, mock_lyrics_service):
        """Test successful lyrics search."""
        response = client.get(
            "/api/lyrics/search?track_name=Bohemian+Rhapsody&artist_name=Queen"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        mock_lyrics_service.search_lyrics.assert_called_once()

    def test_search_requires_track_name(self, client):
        """Test that track_name is required."""
        response = client.get("/api/lyrics/search?artist_name=Queen")

        assert response.status_code == 422

    def test_search_requires_artist_name(self, client):
        """Test that artist_name is required."""
        response = client.get("/api/lyrics/search?track_name=Bohemian+Rhapsody")

        assert response.status_code == 422

    def test_search_with_album_name(self, client, mock_lyrics_service):
        """Test search with optional album name."""
        response = client.get(
            "/api/lyrics/search?track_name=Bohemian+Rhapsody&artist_name=Queen&album_name=A+Night+at+the+Opera"
        )

        assert response.status_code == 200
        # Verify the query includes album name
        call_args = mock_lyrics_service.search_lyrics.call_args[0][0]
        assert "A Night at the Opera" in call_args

    def test_search_builds_correct_query(self, client, mock_lyrics_service):
        """Test that query is built from parameters."""
        response = client.get(
            "/api/lyrics/search?track_name=Test+Song&artist_name=Test+Artist"
        )

        assert response.status_code == 200
        mock_lyrics_service.search_lyrics.assert_called_once_with(
            "Test Artist Test Song"
        )

    def test_search_handles_service_error(self, client, mock_lyrics_service):
        """Test handling of service errors."""
        mock_lyrics_service.search_lyrics.side_effect = Exception("LRCLIB API Error")

        response = client.get("/api/lyrics/search?track_name=test&artist_name=test")

        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()


class TestLyricsSearchErrorPaths:
    """Cover lines 73, 75-76, 81-82 — exception handling in search."""

    def test_search_handles_service_error(self, client, mock_lyrics_service):
        from app.exceptions import ServiceError

        mock_lyrics_service.search_lyrics.side_effect = ServiceError("lyricsdb down")
        response = client.get("/api/lyrics/search?track_name=test&artist_name=me")
        assert response.status_code == 500
        mock_lyrics_service.search_lyrics.side_effect = None

    def test_search_handles_connection_error(self, client, mock_lyrics_service):
        mock_lyrics_service.search_lyrics.side_effect = ConnectionError("unreachable")
        response = client.get("/api/lyrics/search?track_name=test&artist_name=me")
        assert response.status_code == 503
        mock_lyrics_service.search_lyrics.side_effect = None

    def test_search_handles_timeout_error(self, client, mock_lyrics_service):
        mock_lyrics_service.search_lyrics.side_effect = TimeoutError("timed out")
        response = client.get("/api/lyrics/search?track_name=test&artist_name=me")
        assert response.status_code == 504
        mock_lyrics_service.search_lyrics.side_effect = None

    def test_search_handles_unexpected_error(self, client, mock_lyrics_service):
        mock_lyrics_service.search_lyrics.side_effect = RuntimeError("unexpected")
        response = client.get("/api/lyrics/search?track_name=test&artist_name=me")
        assert response.status_code == 500
        mock_lyrics_service.search_lyrics.side_effect = None


class TestSearchLyricsSynced:
    """Cover lines 111-153 — search_lyrics_synced endpoint."""

    def test_search_synced_success(self, client):
        from unittest.mock import MagicMock, patch

        mock_svc = MagicMock()
        mock_svc.search_lyrics_structured.return_value = [
            {"trackName": "Test", "syncedLyrics": "[00:00] Hi"}
        ]
        with patch("app.api.lyrics.SyncedLyricsService", return_value=mock_svc):
            response = client.get(
                "/api/lyrics/search-synced?track_name=Test&artist_name=Me"
            )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_search_synced_with_album(self, client):
        from unittest.mock import MagicMock, patch

        mock_svc = MagicMock()
        mock_svc.search_lyrics_structured.return_value = []
        with patch("app.api.lyrics.SyncedLyricsService", return_value=mock_svc):
            response = client.get(
                "/api/lyrics/search-synced?track_name=Test&artist_name=Me&album_name=Album"
            )
        assert response.status_code == 200
        call_params = mock_svc.search_lyrics_structured.call_args[0][0]
        assert call_params.get("album_name") == "Album"

    def test_search_synced_service_error(self, client):
        from unittest.mock import MagicMock, patch

        from app.exceptions import ServiceError

        mock_svc = MagicMock()
        mock_svc.search_lyrics_structured.side_effect = ServiceError("failed")
        with patch("app.api.lyrics.SyncedLyricsService", return_value=mock_svc):
            response = client.get(
                "/api/lyrics/search-synced?track_name=Test&artist_name=Me"
            )
        assert response.status_code == 500

    def test_search_synced_unexpected_error(self, client):
        from unittest.mock import MagicMock

        mock_svc = MagicMock()
        mock_svc.search_lyrics_structured.side_effect = RuntimeError("boom")
        with patch("app.api.lyrics.SyncedLyricsService", return_value=mock_svc):
            response = client.get(
                "/api/lyrics/search-synced?track_name=Test&artist_name=Me"
            )
        assert response.status_code == 500


class TestManualAlignmentSelection:
    """The /align endpoint now enqueues a background job; source selection is
    validated at the API and forwarded to the worker as a kwarg."""

    def _make_song_with_vocals(self, client, temp_library_dir):
        song = client.post(
            "/api/songs",
            json={"title": "Test Song", "artist": "Test Artist"},
        ).json()
        song_id = song["id"]

        client.post(
            f"/api/lyrics/songs/{song_id}?type=plain",
            json={"content": "plain words"},
        )
        client.post(
            f"/api/lyrics/songs/{song_id}?type=synced",
            json={"content": "[00:00.00]synced words"},
        )

        vocals_path = temp_library_dir / song_id / "vocals.mp3"
        vocals_path.parent.mkdir(parents=True, exist_ok=True)
        vocals_path.write_bytes(b"fake")
        return song_id, vocals_path

    def test_align_defaults_source_to_none(self, client, temp_library_dir):
        song_id, vocals_path = self._make_song_with_vocals(client, temp_library_dir)

        with patch(
            "app.api.lyrics.FileService.get_vocals_path",
            return_value=vocals_path,
        ), patch(
            "app.api.lyrics.enqueue_song_alignment",
            return_value={"status": "pending", "dispatched": True},
        ) as mock_enqueue:
            response = client.post(f"/api/lyrics/songs/{song_id}/align")

        assert response.status_code == 200
        mock_enqueue.assert_called_once()
        # Default (no source query param) forwards source=None to the worker.
        assert mock_enqueue.call_args.kwargs["source"] is None
        assert mock_enqueue.call_args.kwargs["include_remote"] is True

    def test_align_respects_explicit_synced_source(self, client, temp_library_dir):
        song_id, vocals_path = self._make_song_with_vocals(client, temp_library_dir)

        with patch(
            "app.api.lyrics.FileService.get_vocals_path",
            return_value=vocals_path,
        ), patch(
            "app.api.lyrics.enqueue_song_alignment",
            return_value={"status": "pending", "dispatched": True},
        ) as mock_enqueue:
            response = client.post(f"/api/lyrics/songs/{song_id}/align?source=synced")

        assert response.status_code == 200
        mock_enqueue.assert_called_once()
        assert mock_enqueue.call_args.kwargs["source"] == "synced"

    def test_align_rejects_invalid_source(self, client, temp_library_dir):
        song_id, vocals_path = self._make_song_with_vocals(client, temp_library_dir)

        with patch(
            "app.api.lyrics.FileService.get_vocals_path",
            return_value=vocals_path,
        ):
            response = client.post(f"/api/lyrics/songs/{song_id}/align?source=bogus")

        assert response.status_code == 400


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
    with SessionLocal() as session:
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
    client.post(
        f"/api/lyrics/songs/{song_id}?type=plain", json={"content": "Delete me"}
    )
    resp = client.delete(f"/api/lyrics/songs/{song_id}/plain")
    assert resp.status_code == 204
    data = client.get(f"/api/lyrics/songs/{song_id}").json()
    assert data["plainLyrics"] is None


def test_clear_plain_lyrics_clears_alignment(client):
    song_id = _create_song(client)
    client.post(
        f"/api/lyrics/songs/{song_id}?type=plain", json={"content": "Delete me"}
    )
    with SessionLocal() as session:
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
    db = SessionLocal()
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


def test_report_was_wrong_puts_the_reported_lyrics_back(client):
    original = "[00:01.00]Blackbird singing"
    song_id = _song_with_lyrics(client, synced=original)
    with _as_guest(client), _vocals_ready():
        report_id = client.post(
            f"/api/lyrics/songs/{song_id}/reports", json={"kind": "words"}
        ).json()["report"]["id"]
    # The fix replaced the lyrics.
    db = SessionLocal()
    db.get(DbSong, song_id).synced_lyrics = "[00:01.00]what asr heard"
    db.commit()
    db.close()

    with patch("app.api.lyrics.realign_hand_picked_lyrics") as mock_realign:
        resp = client.post(f"/api/lyrics/reports/{report_id}/undo")

    assert resp.status_code == 200
    assert resp.json()["restored"] is True
    song = client.get(f"/api/songs/{song_id}").json()
    assert song["syncedLyrics"] == original
    # An admin vouched for them, so automatic runs only time them now.
    assert song["lyricsHandPicked"] is True
    mock_realign.assert_called_once()
    # The report is gone, and with it the rejection.
    assert client.get("/api/lyrics/reports").json() == []
    from app.repositories.lyrics_report_repository import LyricsReportRepository

    db = SessionLocal()
    assert LyricsReportRepository(db).rejected_keys(song_id) == set()
    db.close()


def test_report_was_wrong_without_kept_lyrics_still_lifts_the_rejection(client):
    from app.db.models import LyricsReport

    song_id = _song_with_lyrics(client)
    db = SessionLocal()
    report = LyricsReport(
        song_id=song_id, kind="words", words_key="old-key", report_count=1
    )
    db.add(report)
    db.commit()
    report_id = report.id
    db.close()

    with _vocals_ready() as mock_enqueue:
        resp = client.post(f"/api/lyrics/reports/{report_id}/undo")

    assert resp.json()["restored"] is False
    assert client.get("/api/lyrics/reports").json() == []
    mock_enqueue.assert_called_once()


def test_undoing_an_unknown_report_is_not_found(client):
    assert client.post("/api/lyrics/reports/999999/undo").status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Library-wide alignment runs
# ─────────────────────────────────────────────────────────────────────────────


@contextmanager
def _vocals_only_for(*song_ids):
    """Only these songs have vocals, so other tests' songs stay out of the counts."""
    with patch("app.services.lyrics_repair.FileService") as mock_files:
        mock_files.return_value.get_vocals_path.side_effect = (
            lambda song_id, ext: SimpleNamespace(exists=lambda: song_id in song_ids)
        )
        yield


def test_alignment_stats_count_songs_needing_repair_by_reason(client):
    import json

    synced_only = _song_with_lyrics(client)
    aligned = _song_with_lyrics(client)
    plain_aligned = _song_with_lyrics(client)
    db = SessionLocal()
    db.get(DbSong, aligned).word_synced_lyrics = json.dumps(
        {
            "words": [
                {
                    "word": "Blackbird",
                    "start": 1.0,
                    "end": 1.4,
                    "score": 0.9,
                    "line_index": 0,
                },
                {
                    "word": "singing",
                    "start": 1.4,
                    "end": 1.9,
                    "score": 0.9,
                    "line_index": 0,
                },
            ],
            "lyrics_source_type": "synced",
        }
    )
    db.get(DbSong, plain_aligned).word_synced_lyrics = json.dumps(
        {"words": [], "lyrics_source_type": "plain"}
    )
    db.commit()
    db.close()

    with _vocals_only_for(synced_only, aligned, plain_aligned):
        resp = client.get("/api/lyrics/batch/align")

    assert resp.status_code == 200
    stats = resp.json()
    assert stats["withVocals"] == 3
    assert stats["aligned"] == 2
    assert stats["needsAlignment"] == 1
    assert stats["repair"] == 2
    assert stats["repairReasons"]["no_word_timing"] == 1
    assert stats["repairReasons"]["plain_timing"] == 1


def test_a_song_with_an_open_report_needs_repair(client):
    song_id = _song_with_lyrics(client)
    with _as_guest(client), _vocals_ready():
        client.post(f"/api/lyrics/songs/{song_id}/reports", json={"kind": "timing"})

    with _vocals_only_for(song_id):
        stats = client.get("/api/lyrics/batch/align").json()

    assert stats["repair"] == 1
    assert stats["repairReasons"]["reported"] == 1
