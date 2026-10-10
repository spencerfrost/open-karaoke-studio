"""
Batch jobs: the library-wide maintenance jobs the admin jobs page runs.

Each job says what it covers (which rows it works on, and which of those still
need it) and which Celery task runs it. The coverage filters here are the same
ones the tasks select with, so "Run on 12 missing" queues exactly those 12.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from app.db.models import BatchRun, DbAlbum, DbArtist, DbSong
from sqlalchemy.orm import Query, Session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchJob:
    kind: str
    # Celery task name; the task takes (mode=..., run_id=...).
    task_name: str
    modes: tuple[str, ...]
    # Every row the job covers, and the ones that still need it.
    covered: Callable[[Session], Query]
    missing: Callable[[Session], Query]


def _songs(session: Session) -> Query:
    return session.query(DbSong.id)


def _artists(session: Session) -> Query:
    return session.query(DbArtist.id)


def _albums(session: Session) -> Query:
    return session.query(DbAlbum.id)


JOBS: dict[str, BatchJob] = {
    job.kind: job
    for job in [
        BatchJob(
            kind="duration",
            task_name="batch_backfill_duration",
            modes=("missing", "all"),
            covered=_songs,
            missing=lambda s: _songs(s).filter(DbSong.duration.is_(None)),
        ),
        BatchJob(
            kind="loudness",
            task_name="batch_backfill_loudness",
            modes=("missing", "all"),
            covered=_songs,
            missing=lambda s: _songs(s).filter(DbSong.loudness_lufs.is_(None)),
        ),
        BatchJob(
            kind="vocal_range",
            task_name="batch_backfill_vocal_range",
            modes=("missing", "all"),
            covered=_songs,
            missing=lambda s: _songs(s).filter(DbSong.vocal_range_low.is_(None)),
        ),
        BatchJob(
            kind="song_albums",
            task_name="batch_backfill_artwork",
            modes=("missing", "all"),
            covered=_songs,
            missing=lambda s: _songs(s).filter(DbSong.album_id.is_(None)),
        ),
        BatchJob(
            kind="album_covers",
            task_name="batch_fetch_album_covers",
            # Only unchecked albums: a found cover is on disk, and one iTunes
            # had no artwork for is marked not_found.
            modes=("missing",),
            covered=_albums,
            missing=lambda s: _albums(s).filter(DbAlbum.image_status == "not_checked"),
        ),
        BatchJob(
            kind="fingerprint",
            task_name="batch_fingerprint_songs",
            modes=("missing", "all"),
            covered=_songs,
            missing=lambda s: _songs(s).filter(
                DbSong.acoustid_fingerprint_status == "not_checked"
            ),
        ),
        BatchJob(
            kind="artist_images",
            task_name="batch_fetch_artist_images",
            # Only unchecked artists: a found image is cached on disk, and
            # re-asking Discogs about every artist only burns rate limit.
            modes=("missing",),
            covered=_artists,
            missing=lambda s: _artists(s).filter(
                DbArtist.image_status == "not_checked"
            ),
        ),
        # Alignment counts come from lyrics_repair instead; see alignment_summary.
        BatchJob(
            kind="lyrics_alignment",
            task_name="batch_align_lyrics",
            modes=("missing", "repair", "all"),
            covered=_songs,
            missing=_songs,
        ),
    ]
}


# The scans an admin runs by hand. They run inside their request and are
# recorded in batch_runs once they finish, so the overview can show the last
# result without scanning again.
SCAN_KINDS = ("disk_check", "metadata_scan", "duplicates")


def record_scan(session: Session, kind: str, *, total: int, issues: int) -> None:
    """Record a finished scan. Never fails the scan: it already has its result."""
    from app.repositories.batch_run_repository import BatchRunRepository

    try:
        BatchRunRepository(session).record_scan(kind, total=total, issues=issues)
    except Exception:
        session.rollback()
        logger.warning("Couldn't record the %s scan", kind, exc_info=True)


class UnknownJob(ValueError):
    pass


class UnsupportedMode(ValueError):
    pass


def get_job(kind: str, mode: Optional[str] = None) -> BatchJob:
    job = JOBS.get(kind)
    if job is None:
        raise UnknownJob(kind)
    if mode is not None and mode not in job.modes:
        raise UnsupportedMode(f"{kind} runs with mode {', '.join(job.modes)}")
    return job


def select_ids(session: Session, kind: str, mode: str) -> list[Any]:
    """The rows a run of `kind` in `mode` works through."""
    job = get_job(kind, mode)
    query = job.missing(session) if mode == "missing" else job.covered(session)
    return [row[0] for row in query.all()]


def alignment_summary(session: Session) -> dict:
    """Alignment coverage and per-mode counts, from the same selection a run uses."""
    from app.services.lyrics_repair import count_reasons, select_songs_for_alignment

    selected, with_vocals = select_songs_for_alignment(session, "all")
    aligned = sum(1 for song, _ in selected if song.word_synced_lyrics)
    needs_repair = [(song, reasons) for song, reasons in selected if reasons]
    return {
        "coverage": {"have": aligned, "of": with_vocals},
        "modeCounts": {
            "missing": with_vocals - aligned,
            "repair": len(needs_repair),
            "all": with_vocals,
        },
        "repairReasons": count_reasons(needs_repair),
    }


def job_summary(session: Session, job: BatchJob) -> dict:
    """What a job covers, how many each mode would run on, plus any details."""
    if job.kind == "lyrics_alignment":
        return alignment_summary(session)
    covered = job.covered(session).count()
    missing = job.missing(session).count()
    return {
        "coverage": {"have": covered - missing, "of": covered},
        "modeCounts": {"missing": missing, "all": covered},
    }


def _iso(value) -> Optional[str]:
    # Columns hold UTC without a zone; say so, or browsers read local time.
    return f"{value.isoformat()}Z" if value else None


def serialize_run(run: Optional[BatchRun]) -> Optional[dict]:
    if run is None:
        return None
    return {
        "id": run.id,
        "kind": run.kind,
        "mode": run.mode,
        "status": run.status,
        "total": run.total,
        "done": run.done,
        "failed": run.failed,
        "error": run.error,
        "issues": run.issues,
        "createdAt": _iso(run.created_at),
        "startedAt": _iso(run.started_at),
        "finishedAt": _iso(run.finished_at),
    }
