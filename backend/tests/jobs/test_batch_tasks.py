"""Tests for the batch tasks that the loudness, vocal range and alignment files don't
cover: fingerprinting, albums, duration and artist images, plus run tracking.

Song and artist rows are real. Outside work is mocked: AcoustID, album lookups,
Discogs, librosa and Celery dispatch.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.db.database import SessionLocal
from app.db.models import BatchRun, DbArtist
from app.jobs.batch_tasks import (
    batch_backfill_duration,
    batch_fetch_albums,
    batch_fetch_artist_images,
    batch_fingerprint_songs,
)
from app.repositories.batch_run_repository import BatchRunRepository


def _add_audio(library, song_id, name):
    song_dir = library / song_id
    song_dir.mkdir(exist_ok=True)
    (song_dir / name).write_bytes(b"fake")
    return song_dir / name


def _new_run(kind, mode="missing"):
    with SessionLocal() as session:
        return BatchRunRepository(session).create(kind, mode).id


def _fetch_run(run_id):
    with SessionLocal() as session:
        return session.get(BatchRun, run_id)


class TestBatchFingerprintSongs:
    @pytest.fixture
    def acoustid(self):
        with patch("app.services.acoustid_service.AcoustIdService") as service_class:
            yield service_class.return_value

    @pytest.fixture
    def send_task(self):
        with patch("app.jobs.batch_tasks.celery.send_task") as send_task:
            yield send_task

    def test_fingerprints_the_best_stem_and_tallies_outcomes(
        self, add_song, fetch_song, library, acoustid, send_task
    ):
        for song_id in ("matched", "unmatched", "broken", "silent"):
            add_song(song_id)
        add_song("done", acoustid_fingerprint_status="matched")
        # The original wins over stems; without it, the instrumental.
        _add_audio(library, "matched", "vocals.mp3")
        original = _add_audio(library, "matched", "original.mp3")
        instrumental = _add_audio(library, "unmatched", "instrumental.mp3")
        _add_audio(library, "broken", "vocals.mp3")
        outcomes = {"matched": "matched", "unmatched": "no_match"}

        def fingerprint(song_id, audio_path):
            if song_id == "broken":
                raise RuntimeError("fpcalc failed")
            return outcomes[song_id]

        acoustid.fingerprint_and_link.side_effect = fingerprint

        result = batch_fingerprint_songs(mode="missing")

        assert result == {"ok": 2, "no_audio": 1, "error": 1}
        paths = {c.args[0]: c.args[1] for c in acoustid.fingerprint_and_link.mock_calls}
        assert paths["matched"] == original
        assert paths["unmatched"] == instrumental
        assert "done" not in paths
        send_task.assert_called_once_with(
            "enrich_song_artist_credits", args=["matched"]
        )
        assert fetch_song("silent").acoustid_fingerprint_status == "failed"

    def test_retry_asks_again_about_unsettled_songs(
        self, add_song, library, acoustid, send_task
    ):
        add_song("no-match", acoustid_fingerprint_status="no_match")
        add_song("unchecked")
        _add_audio(library, "no-match", "original.mp3")
        acoustid.fingerprint_and_link.return_value = "no_match"

        result = batch_fingerprint_songs(mode="retry")

        assert result == {"ok": 1, "no_audio": 0, "error": 0}
        (call,) = acoustid.fingerprint_and_link.mock_calls
        assert call.args[0] == "no-match"


class TestBatchFetchAlbums:
    def test_looks_up_each_song_and_tallies_outcomes(self, add_song):
        for song_id in ("found", "missing", "broken"):
            add_song(song_id)
        outcomes = {"found": "found", "missing": "not_found"}

        def refresh(song_id):
            if song_id == "broken":
                raise RuntimeError("Deezer is down")
            return outcomes[song_id]

        with (
            patch("app.services.album_service.refresh_song_album", side_effect=refresh),
            patch("time.sleep") as sleep,
        ):
            result = batch_fetch_albums(mode="missing")

        assert result == {
            "found": 1,
            "no_cover": 0,
            "not_found": 1,
            "hand_set": 0,
            "error": 1,
            "albums_deleted": 0,
        }
        # A gap between lookups, none before the first.
        assert sleep.call_count == 2


class TestBatchBackfillDuration:
    def test_reads_duration_from_the_original(self, add_song, fetch_song, library):
        add_song("has-audio")
        add_song("no-audio")
        add_song("broken")
        add_song("known", duration=200.0)
        _add_audio(library, "has-audio", "original.mp3")
        _add_audio(library, "broken", "original.mp3")

        def get_duration(path):
            if "broken" in path:
                raise RuntimeError("not an mp3")
            return 191.5

        with patch("librosa.get_duration", side_effect=get_duration):
            result = batch_backfill_duration(mode="missing")

        assert result == {"processed": 3, "success": 1, "skipped": 2}
        assert fetch_song("has-audio").duration == 191.5
        assert fetch_song("no-audio").duration is None
        assert fetch_song("known").duration == 200.0


class TestBatchFetchArtistImages:
    def test_fetches_only_unchecked_artists(self, db, tmp_path):
        db.add_all(
            [
                DbArtist(name="queen", display_name="Queen"),
                DbArtist(name="nobody", display_name="Nobody"),
                DbArtist(name="broken", display_name="Broken"),
                DbArtist(name="done", display_name="Done", image_status="found"),
            ]
        )
        db.commit()
        ids = {a.name: a.id for a in db.query(DbArtist).all()}
        images = {ids["queen"]: tmp_path / "queen.jpg", ids["nobody"]: None}

        async def fetch(artist_id):
            if artist_id == ids["broken"]:
                raise RuntimeError("Discogs is down")
            return images[artist_id]

        with patch(
            "app.services.artist_image_service.ArtistImageService"
        ) as service_class:
            service = service_class.return_value
            service.get_or_fetch_artist_image = AsyncMock(side_effect=fetch)
            result = batch_fetch_artist_images(mode="missing")

        assert result == {"fetched": 1, "not_found": 1, "errors": 1}
        fetched = {c.args[0] for c in service.get_or_fetch_artist_image.await_args_list}
        assert fetched == {ids["queen"], ids["nobody"], ids["broken"]}

    def test_no_unchecked_artists_is_an_empty_run(self):
        assert batch_fetch_artist_images(mode="missing") == {
            "fetched": 0,
            "not_found": 0,
            "errors": 0,
        }


class TestRunTracking:
    def test_records_progress_and_closes_the_run(self, add_song, library):
        add_song("has-audio")
        add_song("broken")
        _add_audio(library, "has-audio", "original.mp3")
        _add_audio(library, "broken", "original.mp3")
        run_id = _new_run("duration")

        def get_duration(path):
            if "broken" in path:
                raise RuntimeError("not an mp3")
            return 191.5

        with patch("librosa.get_duration", side_effect=get_duration):
            batch_backfill_duration(mode="missing", run_id=run_id)

        run = _fetch_run(run_id)
        assert (run.status, run.total, run.done, run.failed) == ("done", 2, 1, 1)
        assert run.finished_at is not None

    def test_a_cancelled_run_stops_before_the_next_song(self, add_song, library):
        add_song("first")
        add_song("second")
        run_id = _new_run("duration")
        with SessionLocal() as session:
            repo = BatchRunRepository(session)
            repo.cancel(repo.get(run_id))

        with patch("librosa.get_duration") as get_duration:
            result = batch_backfill_duration(mode="missing", run_id=run_id)

        get_duration.assert_not_called()
        assert result == {"processed": 0, "success": 0, "skipped": 0}
        assert _fetch_run(run_id).status == "cancelled"

    def test_a_crash_fails_the_run_with_its_error(self):
        run_id = _new_run("duration")

        with patch(
            "app.jobs.batch_tasks._select", side_effect=RuntimeError("database gone")
        ):
            with pytest.raises(RuntimeError):
                batch_backfill_duration(mode="missing", run_id=run_id)

        run = _fetch_run(run_id)
        assert run.status == "failed"
        assert run.error == "RuntimeError: database gone"
