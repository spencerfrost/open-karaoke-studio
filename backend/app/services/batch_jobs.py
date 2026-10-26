"""
Batch jobs: the library-wide maintenance jobs the admin jobs page runs.

Each job says what it covers (which rows it works on, and which of those still
need it) and which Celery task runs it. The coverage filters here are the same
ones the tasks select with, so "Run on 12 missing" queues exactly those 12.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.db.models import BatchRun, DbAlbum, DbArtist, DbSong, DbSongArtist

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
    # Rows for modes other than "missing" and "all".
    others: dict[str, Callable[[Session], Query]] = field(default_factory=dict)
    # Whether a finished run saves a report (GET /admin/jobs/runs/{id}/report).
    reports: bool = False

    def rows(self, session: Session, mode: str) -> Query:
        """The rows a run in `mode` works through: "all" is every covered row."""
        if mode == "missing":
            return self.missing(session)
        if mode == "all":
            return self.covered(session)
        return self.others[mode](session)


def _songs(session: Session) -> Query:
    return session.query(DbSong.id)


def _artists(session: Session) -> Query:
    return session.query(DbArtist.id)


def _songs_with_old_credits(session: Session) -> Query:
    """Songs credited before credits came as lists: no credits, or a credit
    without the name it was printed as."""
    has_list = session.query(DbSongArtist.song_id).filter(
        DbSongArtist.song_id == DbSong.id
    )
    old = has_list.filter(DbSongArtist.credited_as.is_(None))
    return _songs(session).filter(or_(~has_list.exists(), old.exists()))


def _songs_without_hand_set_album(session: Session) -> Query:
    return _songs(session).filter(DbSong.album_hand_set_at.is_(None))


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
            task_name="batch_fetch_albums",
            modes=("missing", "all"),
            covered=_songs_without_hand_set_album,
            # Not checked yet, and no album or an album without a cover. A
            # song the lookup found nothing for is checked; "all" asks again.
            missing=lambda s: _songs_without_hand_set_album(s)
            .outerjoin(DbAlbum, DbSong.album_id == DbAlbum.id)
            .filter(
                DbSong.album_checked_at.is_(None),
                or_(DbSong.album_id.is_(None), DbAlbum.cover_path.is_(None)),
            ),
        ),
        BatchJob(
            kind="fingerprint",
            task_name="batch_fingerprint_songs",
            # No "all": fingerprinting a song again only re-asks AcoustID, and
            # matched or hand-confirmed songs have nothing to gain from that.
            # "retry" re-asks about unconfirmed songs it couldn't settle: no
            # match or a failed lookup (its database may have caught up), and
            # ambiguous ties (one of them may be named like the song).
            modes=("missing", "retry"),
            covered=_songs,
            missing=lambda s: _songs(s).filter(
                DbSong.acoustid_fingerprint_status == "not_checked"
            ),
            others={
                "retry": lambda s: _songs(s).filter(
                    DbSong.acoustid_fingerprint_status.in_(
                        ("ambiguous", "no_match", "failed")
                    ),
                    DbSong.metadata_confirmed_at.is_(None),
                )
            },
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
        BatchJob(
            kind="artist_credits",
            task_name="batch_rebuild_artist_credits",
            # Both run over the whole library; "preview" changes nothing.
            modes=("preview", "apply"),
            covered=_songs,
            missing=_songs_with_old_credits,
            others={"preview": _songs, "apply": _songs},
            reports=True,
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
    query = job.rows(session, mode)
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
    counts = {"missing": missing, "all": covered}
    for mode in job.others:
        counts[mode] = job.rows(session, mode).count()
    return {
        "coverage": {"have": covered - missing, "of": covered},
        "modeCounts": counts,
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
        # Read off the job, not the column: reports are large.
        "hasReport": run.status == "done"
        and run.kind in JOBS
        and JOBS[run.kind].reports,
        "createdAt": _iso(run.created_at),
        "startedAt": _iso(run.started_at),
        "finishedAt": _iso(run.finished_at),
    }
