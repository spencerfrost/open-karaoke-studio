"""Tests for the admin overview and the hand-run scans it reports."""

from datetime import timedelta
from unittest.mock import patch

import pytest

from app.db.models import BatchRun, DbSong, LyricsReport
from app.repositories.batch_run_repository import BatchRunRepository
from app.services.processing_versions import LOUDNESS_VERSION
from app.utils.clock import utc_now


@pytest.fixture(autouse=True)
def no_alignment_scan():
    # Alignment selection looks for vocals files on disk; it has its own tests.
    with patch(
        "app.services.lyrics_repair.select_songs_for_alignment",
        return_value=([], 0),
    ):
        yield


def _add(db, song_id, **fields):
    fields.setdefault("title", song_id)
    fields.setdefault("artist", "Queen")
    db.add(DbSong(id=song_id, **fields))
    db.commit()


def _overview(client):
    resp = client.get("/api/admin/overview")
    assert resp.status_code == 200
    return resp.json()


class TestOverview:
    def test_counts_what_needs_reviewing(self, client, db):
        _add(db, "fine")
        _add(db, "renamed", acoustid_fingerprint_status="suggested")
        _add(db, "unsure", acoustid_fingerprint_status="ambiguous")
        _add(db, "unknown", acoustid_fingerprint_status="no_match")
        _add(db, "unknown-2", acoustid_fingerprint_status="no_match")
        _add(db, "broken", status="error")
        db.add(
            LyricsReport(song_id="fine", kind="words", words_key="k", report_count=1)
        )
        db.add(
            LyricsReport(
                song_id="unsure",
                kind="timing",
                words_key="k",
                report_count=1,
                resolved_at=utc_now(),
            )
        )
        db.commit()

        body = _overview(client)

        assert body["needsYou"] == {
            "lyricsReports": 1,
            "acoustid": {"suggested": 1, "ambiguous": 1, "noMatch": 2, "failed": 0},
            "failedSongs": 1,
            "alignmentRepair": 0,
        }
        # Failed songs aren't in the songbook.
        assert body["librarySize"] == 5

    def test_reports_coverage_and_runs_in_progress(self, client, db):
        _add(db, "a", loudness_lufs=-9.0, loudness_version=LOUDNESS_VERSION)
        _add(db, "b")
        run = BatchRunRepository(db).create("loudness", "missing")

        jobs = {job["kind"]: job for job in _overview(client)["jobs"]}

        assert jobs["loudness"]["coverage"] == {"have": 1, "of": 2}
        assert jobs["loudness"]["activeRun"]["id"] == run.id
        assert jobs["duration"]["activeRun"] is None

    def test_songs_added_per_week_oldest_first(self, client, db):
        now = utc_now()
        _add(db, "today", date_added=now - timedelta(hours=1))
        _add(db, "also-this-week", date_added=now - timedelta(days=6))
        _add(db, "last-week", date_added=now - timedelta(days=8))
        _add(db, "too-old", date_added=now - timedelta(weeks=13))

        added = _overview(client)["songsAdded"]

        counts = [week["count"] for week in added["weeks"]]
        assert len(counts) == 12
        assert counts[-1] == 2
        assert counts[-2] == 1
        assert sum(counts) == 3
        assert [song["id"] for song in added["recent"]][:3] == [
            "today",
            "also-this-week",
            "last-week",
        ]

    def test_scans_show_their_last_finished_run(self, client, db):
        repo = BatchRunRepository(db)
        repo.record_scan("duplicates", total=100, issues=7)
        latest = repo.record_scan("duplicates", total=101, issues=3)

        scans = _overview(client)["scans"]

        assert scans["duplicates"]["id"] == latest.id
        assert scans["duplicates"]["issues"] == 3
        assert scans["disk_check"] is None
        assert scans["metadata_scan"] is None


class TestScansAreRecorded:
    def _last(self, db, kind):
        return (
            db.query(BatchRun)
            .filter(BatchRun.kind == kind)
            .order_by(BatchRun.id.desc())
            .first()
        )

    def test_metadata_scan(self, client, db):
        _add(db, "good", album="A Night at the Opera", duration=200)
        _add(db, "nameless", title="", duration=200)

        resp = client.get("/api/songs/metadata-audit")

        assert resp.status_code == 200
        run = self._last(db, "metadata_scan")
        assert (run.status, run.total, run.issues) == (
            "done",
            2,
            resp.json()["total_flagged"],
        )

    def test_duplicates_scan(self, client, db):
        _add(db, "one", title="Hey Jude", artist="The Beatles")
        _add(db, "two", title="hey jude", artist="the beatles")
        _add(db, "other", title="Let It Be", artist="The Beatles")

        resp = client.get("/api/songs/duplicates")

        assert resp.status_code == 200
        run = self._last(db, "duplicates")
        assert (run.total, run.issues) == (3, 1)

    def test_disk_check(self, client, db):
        _add(db, "ghost")
        with patch("app.api.songs.FileService") as file_service:
            file_service.return_value.get_processed_song_ids.return_value = ["orphan"]
            file_service.return_value.list_song_files.return_value = []

            resp = client.get("/api/songs/library-audit")

        assert resp.status_code == 200
        run = self._last(db, "disk_check")
        # One folder with no song, one song with no folder.
        assert (run.total, run.issues) == (2, 2)

    def test_scans_stay_off_the_jobs_page_runs(self, client, db):
        BatchRunRepository(db).record_scan("duplicates", total=10, issues=1)

        runs = client.get("/api/admin/jobs/runs").json()["runs"]

        assert runs == []
