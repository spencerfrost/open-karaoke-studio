"""Tests for the admin background jobs API and batch run progress tracking."""

from datetime import timedelta
from unittest.mock import Mock, patch

import pytest

from app.db.models import BatchRun, DbAlbum, DbArtist, DbSong
from app.jobs._batch_runs import RunTracker, tracked_run
from app.repositories.batch_run_repository import (
    STALE_AFTER,
    BatchRunRepository,
    RunNotActive,
    utc_now,
)
from app.services.batch_jobs import select_ids

NO_ALIGNMENT = ([], 0)


@pytest.fixture
def mock_celery():
    with patch("app.api.admin.celery") as celery:
        celery.send_task.return_value = Mock(id="task-1")
        yield celery


@pytest.fixture(autouse=True)
def no_alignment_scan():
    # Alignment selection looks for vocals files on disk; it has its own tests.
    with patch(
        "app.services.lyrics_repair.select_songs_for_alignment",
        return_value=NO_ALIGNMENT,
    ):
        yield


def _add_songs(db, *songs):
    for song_id, loudness in songs:
        db.add(
            DbSong(id=song_id, title=song_id, artist="Queen", loudness_lufs=loudness)
        )
    db.commit()


def _jobs_by_kind(client):
    resp = client.get("/api/admin/jobs")
    assert resp.status_code == 200
    return {job["kind"]: job for job in resp.json()["jobs"]}


class TestListJobs:
    def test_coverage_counts_what_each_job_still_needs(self, client, db):
        _add_songs(db, ("a", -9.0), ("b", None), ("c", None))

        loudness = _jobs_by_kind(client)["loudness"]

        assert loudness["coverage"] == {"have": 1, "of": 3}
        assert loudness["modeCounts"] == {"missing": 2, "all": 3}
        assert loudness["modes"] == ["missing", "all"]
        assert loudness["lastRun"] is None
        assert loudness["activeRun"] is None

    def test_artist_images_only_run_on_unchecked_artists(self, client, db):
        db.add(DbArtist(name="queen", image_status="found"))
        db.add(DbArtist(name="abba", image_status="not_checked"))
        db.commit()

        images = _jobs_by_kind(client)["artist_images"]

        assert images["coverage"] == {"have": 1, "of": 2}
        assert images["modes"] == ["missing"]

    def test_song_albums_skip_hand_set_checked_and_covered_songs(self, client, db):
        covered = DbAlbum(title="Rumours", cover_path="covers/album-1.jpg")
        bare = DbAlbum(title="Tusk")
        db.add_all([covered, bare])
        db.commit()
        for song_id, album_id, hand_set, checked in [
            ("no-album", None, False, False),
            ("bare-album", bare.id, False, False),
            ("covered", covered.id, False, False),
            ("checked", None, False, True),
            ("hand-set", None, True, False),
        ]:
            db.add(
                DbSong(
                    id=song_id,
                    title=song_id,
                    artist="Fleetwood Mac",
                    album_id=album_id,
                    album_hand_set_at=utc_now() if hand_set else None,
                    album_checked_at=utc_now() if checked else None,
                )
            )
        db.commit()

        albums = _jobs_by_kind(client)["song_albums"]

        assert albums["modes"] == ["missing", "all"]
        assert albums["modeCounts"] == {"missing": 2, "all": 4}
        assert sorted(select_ids(db, "song_albums", "missing")) == [
            "bare-album",
            "no-album",
        ]
        assert "hand-set" not in select_ids(db, "song_albums", "all")

    def test_fingerprint_retries_unconfirmed_unsettled_songs(self, client, db):
        for song_id, status, confirmed in [
            ("new", "not_checked", False),
            ("none", "no_match", False),
            ("broke", "failed", False),
            ("tied", "ambiguous", False),
            ("tied-kept", "ambiguous", True),
            ("kept", "no_match", True),
            ("ok", "matched", False),
            ("review", "suggested", False),
        ]:
            db.add(
                DbSong(
                    id=song_id,
                    title=song_id,
                    artist="Queen",
                    acoustid_fingerprint_status=status,
                    metadata_confirmed_at=utc_now() if confirmed else None,
                )
            )
        db.commit()

        fingerprint = _jobs_by_kind(client)["fingerprint"]

        assert fingerprint["modes"] == ["missing", "retry"]
        assert fingerprint["modeCounts"]["missing"] == 1
        assert fingerprint["modeCounts"]["retry"] == 3
        assert sorted(select_ids(db, "fingerprint", "retry")) == [
            "broke",
            "none",
            "tied",
        ]

    def test_lists_every_job(self, client):
        assert set(_jobs_by_kind(client)) == {
            "duration",
            "loudness",
            "vocal_range",
            "song_albums",
            "fingerprint",
            "artist_images",
            "lyrics_alignment",
        }

    def test_a_running_row_that_stopped_reporting_is_closed(self, client, db):
        run = BatchRunRepository(db).create("loudness", "missing")
        run.status = "running"
        run.updated_at = utc_now() - STALE_AFTER - timedelta(minutes=1)
        db.commit()

        loudness = _jobs_by_kind(client)["loudness"]

        assert loudness["activeRun"] is None
        assert loudness["lastRun"]["status"] == "failed"
        assert "Stopped reporting" in loudness["lastRun"]["error"]


class TestRunJob:
    def test_creates_a_queued_run_and_sends_its_task(self, client, db, mock_celery):
        resp = client.post("/api/admin/jobs/loudness/run?mode=all")

        assert resp.status_code == 202
        run = resp.json()["run"]
        assert run["status"] == "queued"
        assert run["mode"] == "all"
        mock_celery.send_task.assert_called_once_with(
            "batch_backfill_loudness", kwargs={"mode": "all", "run_id": run["id"]}
        )
        assert db.get(BatchRun, run["id"]).celery_task_id == "task-1"

    def test_one_run_per_job_at_a_time(self, client, mock_celery):
        client.post("/api/admin/jobs/loudness/run")

        resp = client.post("/api/admin/jobs/loudness/run")

        assert resp.status_code == 409
        assert mock_celery.send_task.call_count == 1

    def test_other_jobs_can_run_alongside(self, client, mock_celery):
        client.post("/api/admin/jobs/loudness/run")

        assert client.post("/api/admin/jobs/duration/run").status_code == 202

    def test_unknown_job(self, client, mock_celery):
        assert client.post("/api/admin/jobs/nope/run").status_code == 404

    def test_mode_the_job_does_not_have(self, client, mock_celery):
        assert (
            client.post("/api/admin/jobs/artist_images/run?mode=all").status_code == 400
        )
        assert (
            client.post("/api/admin/jobs/fingerprint/run?mode=all").status_code == 400
        )
        assert (
            client.post("/api/admin/jobs/fingerprint/run?mode=retry").status_code == 202
        )
        assert (
            client.post("/api/admin/jobs/lyrics_alignment/run?mode=repair").status_code
            == 202
        )

    def test_a_broker_failure_fails_the_run(self, client, db, mock_celery):
        mock_celery.send_task.side_effect = ConnectionError("redis down")

        resp = client.post("/api/admin/jobs/loudness/run")

        assert resp.status_code == 503
        assert db.query(BatchRun).one().status == "failed"


class TestCancelRun:
    def test_cancels_and_revokes(self, client, mock_celery):
        run_id = client.post("/api/admin/jobs/loudness/run").json()["run"]["id"]

        resp = client.post(f"/api/admin/jobs/runs/{run_id}/cancel")

        assert resp.status_code == 200
        assert resp.json()["run"]["status"] == "cancelled"
        mock_celery.control.revoke.assert_called_once_with("task-1")
        # Cancelled frees the job for another run.
        assert client.post("/api/admin/jobs/loudness/run").status_code == 202

    def test_a_finished_run_cannot_be_cancelled(self, client, db, mock_celery):
        run = BatchRunRepository(db).create("loudness", "missing")
        BatchRunRepository(db).finish(run.id)

        assert client.post(f"/api/admin/jobs/runs/{run.id}/cancel").status_code == 409


class TestRecentRuns:
    def test_newest_first(self, client, db):
        repo = BatchRunRepository(db)
        first = repo.create("loudness", "missing")
        second = repo.create("duration", "all")

        runs = client.get("/api/admin/jobs/runs").json()["runs"]

        assert [run["id"] for run in runs] == [second.id, first.id]
        assert runs[0]["createdAt"].endswith("Z")


class TestWorkers:
    def test_reports_queues_nobody_serves(self, client):
        with patch("app.api.admin.celery") as celery:
            celery.control.inspect.return_value.active_queues.return_value = {
                "audio@box": [{"name": "audio"}],
                "enrichment@box": [{"name": "enrichment"}],
            }
            body = client.get("/api/admin/workers").json()

        assert body["brokerReachable"] is True
        assert body["workers"] == ["audio@box", "enrichment@box"]
        assert body["queues"] == [
            {"queue": "audio", "workers": ["audio@box"]},
            {"queue": "enrichment", "workers": ["enrichment@box"]},
            {"queue": "lyrics", "workers": []},
        ]

    def test_no_workers_answering(self, client):
        with patch("app.api.admin.celery") as celery:
            celery.control.inspect.return_value.active_queues.return_value = None
            body = client.get("/api/admin/workers").json()

        assert body["workers"] == []
        assert all(queue["workers"] == [] for queue in body["queues"])

    def test_broker_unreachable(self, client):
        with patch("app.api.admin.celery") as celery:
            celery.control.inspect.side_effect = ConnectionError("redis down")
            body = client.get("/api/admin/workers").json()

        assert body["brokerReachable"] is False


class TestRunTracker:
    def test_counts_songs_and_closes_the_run(self, db):
        run = BatchRunRepository(db).create("loudness", "missing")

        with tracked_run(run.id) as tracker:
            tracker.start(3)
            tracker.song_done()
            tracker.song_done()
            tracker.song_done(ok=False)

        db.refresh(run)
        assert (run.status, run.total, run.done, run.failed) == ("done", 3, 2, 1)
        assert run.started_at is not None and run.finished_at is not None

    def test_a_crash_fails_the_run_and_still_raises(self, db):
        run = BatchRunRepository(db).create("loudness", "missing")

        with pytest.raises(RuntimeError):
            with tracked_run(run.id) as tracker:
                tracker.start(2)
                raise RuntimeError("ffmpeg missing")

        db.refresh(run)
        assert run.status == "failed"
        assert run.error == "RuntimeError: ffmpeg missing"

    def test_a_cancelled_run_stops_before_the_next_song(self, db):
        repo = BatchRunRepository(db)
        run = repo.create("loudness", "missing")
        handled = []

        with tracked_run(run.id) as tracker:
            tracker.start(3)
            for song in ["a", "b", "c"]:
                handled.append(song)
                if song == "a":
                    repo.cancel(repo.get(run.id))
                tracker.song_done()

        db.refresh(run)
        assert handled == ["a"]
        assert run.status == "cancelled"

    def test_cancelled_while_queued_never_starts(self, db):
        repo = BatchRunRepository(db)
        run = repo.create("loudness", "missing")
        repo.cancel(run)
        started = []

        with tracked_run(run.id) as tracker:
            tracker.start(3)
            started.append(True)

        assert started == []

    def test_without_a_run_id_nothing_is_recorded(self, db):
        with tracked_run(None) as tracker:
            tracker.start(1)
            tracker.song_done()

        assert db.query(BatchRun).count() == 0

    def test_a_failed_progress_write_does_not_stop_the_work(self):
        with patch("app.db.database.get_db_session", side_effect=OSError("db gone")):
            RunTracker(1).song_done()  # logged, not raised

    def test_cancel_check_raises_run_not_active(self, db):
        repo = BatchRunRepository(db)
        run = repo.create("loudness", "missing")
        repo.cancel(run)

        with pytest.raises(RunNotActive):
            repo.advance(run.id, ok=True)
