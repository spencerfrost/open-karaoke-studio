"""Tests for the admin background jobs API and batch run progress tracking."""

from datetime import timedelta
from unittest.mock import Mock, patch

import pytest

from app.db.models import BatchRun, DbAlbum, DbArtist, DbSong, DbSongArtist
from app.jobs._batch_runs import RunTracker, tracked_run
from app.repositories.batch_run_repository import (
    STALE_AFTER,
    BatchRunRepository,
    RunNotActive,
)
from app.services.batch_jobs import select_ids
from app.services.processing_versions import LOUDNESS_VERSION
from app.utils.clock import utc_now

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
            DbSong(
                id=song_id,
                title=song_id,
                artist="Queen",
                loudness_lufs=loudness,
                loudness_version=None if loudness is None else LOUDNESS_VERSION,
            )
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

    def test_album_art_videos_cover_youtube_songs_not_yet_looked_at(self, client, db):
        db.add_all(
            [
                DbSong(id="new", title="New", artist="A", video_id="v1"),
                DbSong(
                    id="seen",
                    title="Seen",
                    artist="A",
                    video_id="v2",
                    video_is_album_art=False,
                ),
                DbSong(id="upload", title="Upload", artist="A"),
            ]
        )
        db.commit()

        videos = _jobs_by_kind(client)["album_art_videos"]

        assert videos["coverage"] == {"have": 1, "of": 2}
        assert select_ids(db, "album_art_videos", "missing") == ["new"]
        assert sorted(select_ids(db, "album_art_videos", "all")) == ["new", "seen"]

    def test_lists_every_job(self, client):
        assert set(_jobs_by_kind(client)) == {
            "duration",
            "loudness",
            "singing_map",
            "vocal_range",
            "song_albums",
            "album_art_videos",
            "fingerprint",
            "artist_images",
            "lyrics_alignment",
            "artist_credits",
            "lrc_offset",
        }

    def test_artist_credits_counts_songs_with_old_credits(self, client, db):
        db.add_all(
            [
                DbArtist(id=1, name="a", display_name="A"),
                DbSong(id="old", title="Old", artist="A"),
                DbSong(id="new", title="New", artist="A"),
                DbSong(id="none", title="None", artist="A"),
                DbSongArtist(song_id="old", artist_id=1, role="primary"),
                DbSongArtist(
                    song_id="new", artist_id=1, role="primary", credited_as="A"
                ),
            ]
        )
        db.commit()

        job = _jobs_by_kind(client)["artist_credits"]

        assert job["modes"] == ["preview", "apply"]
        assert job["coverage"] == {"have": 1, "of": 3}
        assert job["modeCounts"]["preview"] == 3

    def test_a_running_row_that_stopped_reporting_is_interrupted(self, client, db):
        run = BatchRunRepository(db).create("loudness", "missing")
        run.status = "running"
        run.updated_at = utc_now() - STALE_AFTER - timedelta(minutes=1)
        db.commit()

        loudness = _jobs_by_kind(client)["loudness"]

        # Still active: it carries on when the enrichment worker starts.
        assert loudness["activeRun"]["status"] == "interrupted"
        assert "Stopped reporting" in loudness["activeRun"]["error"]


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
            {"queue": "lyrics_backfill", "workers": []},
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


class TestRunReport:
    def test_returns_the_saved_report(self, client, db):
        run = BatchRunRepository(db).create("artist_credits", "preview")
        run.status = "done"
        run.report = {"mode": "preview"}
        db.commit()

        resp = client.get(f"/api/admin/jobs/runs/{run.id}/report")

        assert resp.status_code == 200
        assert resp.json()["report"] == {"mode": "preview"}
        assert resp.json()["run"]["hasReport"] is True

    def test_a_run_without_one_is_404(self, client, db):
        run = BatchRunRepository(db).create("loudness", "missing")

        assert client.get(f"/api/admin/jobs/runs/{run.id}/report").status_code == 404


class TestPauseRun:
    def _run(self, db, status, **fields):
        repo = BatchRunRepository(db)
        run = repo.create("loudness", "missing")
        run.status = status
        run.celery_task_id = "task-0"
        for name, value in fields.items():
            setattr(run, name, value)
        db.commit()
        return run.id

    def test_a_running_run_pauses_after_its_song(self, client, db, mock_celery):
        run_id = self._run(db, "running")

        resp = client.post(f"/api/admin/jobs/runs/{run_id}/pause")

        assert resp.status_code == 200
        assert resp.json()["run"]["status"] == "pausing"
        mock_celery.control.revoke.assert_not_called()

    def test_a_queued_run_pauses_now_and_its_task_is_dropped(
        self, client, db, mock_celery
    ):
        run_id = self._run(db, "queued")

        resp = client.post(f"/api/admin/jobs/runs/{run_id}/pause")

        assert resp.json()["run"]["status"] == "paused"
        mock_celery.control.revoke.assert_called_once_with("task-0")

    def test_resume_queues_the_task_again(self, client, db, mock_celery):
        run_id = self._run(db, "paused")

        resp = client.post(f"/api/admin/jobs/runs/{run_id}/resume")

        assert resp.status_code == 200
        assert resp.json()["run"]["status"] == "queued"
        mock_celery.send_task.assert_called_once_with(
            "batch_backfill_loudness", kwargs={"mode": "missing", "run_id": run_id}
        )
        db.expire_all()
        assert db.get(BatchRun, run_id).celery_task_id == "task-1"

    def test_resume_while_pausing_lets_the_task_carry_on(self, client, db, mock_celery):
        run_id = self._run(db, "pausing")

        resp = client.post(f"/api/admin/jobs/runs/{run_id}/resume")

        assert resp.json()["run"]["status"] == "running"
        mock_celery.send_task.assert_not_called()

    def test_a_finished_run_cannot_be_paused_or_resumed(self, client, db, mock_celery):
        run_id = self._run(db, "done")

        assert client.post(f"/api/admin/jobs/runs/{run_id}/pause").status_code == 409
        assert client.post(f"/api/admin/jobs/runs/{run_id}/resume").status_code == 409

    def test_a_paused_run_can_be_stopped(self, client, db, mock_celery):
        run_id = self._run(db, "paused")

        resp = client.post(f"/api/admin/jobs/runs/{run_id}/cancel")

        assert resp.json()["run"]["status"] == "cancelled"

    def test_a_handed_off_run_takes_its_queued_songs_off_and_queues_them_on_resume(
        self, client, db, mock_celery
    ):
        db.add_all([DbSong(id="s1", title="One"), DbSong(id="s2", title="Two")])
        db.commit()
        run_id = self._run(
            db,
            "running",
            kind="lyrics_alignment",
            mode="retime",
            total=3,
            report={"waitingOnJobs": ["j0", "j1", "j2"]},
        )

        with patch(
            "app.jobs.lyrics_dispatch.take_queued_alignments_off",
            return_value=["s1", "s2"],
        ) as take_off:
            resp = client.post(f"/api/admin/jobs/runs/{run_id}/pause")

        take_off.assert_called_once_with(["j0", "j1", "j2"])
        assert resp.json()["run"]["status"] == "paused"
        # The worker that aligned gives its GPU memory back after its song.
        mock_celery.send_task.assert_called_once_with(
            "release_gpu_memory", kwargs={"reason": f"batch run {run_id} paused"}
        )

        with patch("app.jobs.lyrics_dispatch.enqueue_song_alignment") as enqueue:
            resp = client.post(f"/api/admin/jobs/runs/{run_id}/resume")

        assert resp.json()["run"]["status"] == "running"
        assert sorted(call.args[0].id for call in enqueue.call_args_list) == [
            "s1",
            "s2",
        ]
        assert all(
            call.kwargs == {"include_remote": False, "background": True}
            for call in enqueue.call_args_list
        )
        db.expire_all()
        assert db.get(BatchRun, run_id).report == {"waitingOnJobs": ["j0", "j1", "j2"]}
