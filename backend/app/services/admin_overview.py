"""
Admin overview: the counts the admin landing page shows.

Everything here is a count or a short list read straight from the database,
so the page can poll it. The slow scans (disk check, metadata, duplicates)
are not re-run; their last recorded run is reported instead.
"""

from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import DbSong, LyricsReport
from app.db.models.song import in_songbook
from app.repositories.batch_run_repository import BatchRunRepository, utc_now
from app.services.batch_jobs import JOBS, SCAN_KINDS, job_summary, serialize_run

SONGS_ADDED_WEEKS = 12
RECENT_SONGS = 6
REVIEW_FINGERPRINT_STATUSES = ("ambiguous", "no_match", "failed")


def _acoustid_counts(db: Session) -> dict:
    rows = (
        db.query(DbSong.acoustid_fingerprint_status, func.count(DbSong.id))
        .filter(DbSong.acoustid_fingerprint_status.in_(REVIEW_FINGERPRINT_STATUSES))
        .group_by(DbSong.acoustid_fingerprint_status)
        .all()
    )
    counts = dict(rows)
    return {
        "ambiguous": counts.get("ambiguous", 0),
        "noMatch": counts.get("no_match", 0),
        "failed": counts.get("failed", 0),
    }


def _songs_added(db: Session) -> dict:
    """Songs added per week, oldest week first. Weeks count back from now,
    so the last one is the past seven days."""
    now = utc_now()
    since = now - timedelta(weeks=SONGS_ADDED_WEEKS)
    counts = [0] * SONGS_ADDED_WEEKS
    for (added,) in db.query(DbSong.date_added).filter(DbSong.date_added >= since):
        weeks_ago = (now - added.replace(tzinfo=None)).days // 7
        if 0 <= weeks_ago < SONGS_ADDED_WEEKS:
            counts[SONGS_ADDED_WEEKS - 1 - weeks_ago] += 1

    weeks = [
        {
            "start": (now - timedelta(weeks=SONGS_ADDED_WEEKS - i)).date().isoformat(),
            "count": count,
        }
        for i, count in enumerate(counts)
    ]

    recent = (
        db.query(DbSong)
        .filter(DbSong.date_added.isnot(None))
        .order_by(DbSong.date_added.desc())
        .limit(RECENT_SONGS)
        .all()
    )
    return {
        "weeks": weeks,
        "recent": [
            {
                "id": song.id,
                "title": song.title,
                "artist": song.artist,
                "status": song.status,
                "dateAdded": f"{song.date_added.replace(tzinfo=None).isoformat()}Z",
            }
            for song in recent
        ],
    }


def build_overview(db: Session) -> dict:
    repo = BatchRunRepository(db)
    repo.close_stale()

    jobs = []
    alignment_repair = 0
    for job in JOBS.values():
        summary = job_summary(db, job)
        if job.kind == "lyrics_alignment":
            alignment_repair = summary["modeCounts"]["repair"]
        jobs.append(
            {
                "kind": job.kind,
                "coverage": summary["coverage"],
                "activeRun": serialize_run(repo.active(job.kind)),
            }
        )

    library_size = db.query(func.count(DbSong.id)).filter(in_songbook()).scalar()
    open_reports = (
        db.query(func.count(LyricsReport.id))
        .filter(LyricsReport.resolved_at.is_(None))
        .scalar()
    )
    failed_songs = (
        db.query(func.count(DbSong.id)).filter(DbSong.status == "error").scalar()
    )

    return {
        "librarySize": library_size,
        "needsYou": {
            "lyricsReports": open_reports,
            "acoustid": _acoustid_counts(db),
            "failedSongs": failed_songs,
            "alignmentRepair": alignment_repair,
        },
        "jobs": jobs,
        "songsAdded": _songs_added(db),
        "scans": {kind: serialize_run(repo.last_finished(kind)) for kind in SCAN_KINDS},
    }
