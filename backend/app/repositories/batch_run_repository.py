"""
Batch run repository: the record of every batch job run.
"""

from datetime import timedelta
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.db.models import BatchRun
from app.utils.clock import utc_now

# "interrupted" is active: the run carries on when an enrichment worker starts.
# "pausing": someone pressed Pause and the task stops after the song it's on;
# "paused": stopped, and stays stopped until someone presses Resume.
ACTIVE_STATUSES = ("queued", "running", "interrupted", "pausing", "paused")

# A running task reports after every song, and no song takes anywhere near
# this long. A running row this quiet belongs to a worker that died.
STALE_AFTER = timedelta(minutes=15)
STALE_MESSAGE = (
    "Stopped reporting progress. It carries on when the enrichment worker starts."
)

# A run whose task hands its songs to other jobs (lyrics alignment queues one
# job per song) keeps those jobs' ids under this report key while it waits.
WAITING_ON_KEY = "waitingOnJobs"
# Job statuses that mean a handed-off song hasn't finished.
_UNFINISHED_JOB_STATUSES = ("pending", "downloading", "processing")


# Report key of a handed-off run that's paused: the songs whose queued jobs
# were taken off the queue, to queue again on Resume.
PAUSED_SONGS_KEY = "pausedSongIds"


class RunNotActive(Exception):
    """The run was cancelled, or closed as stale, while its task still had work."""


class RunPaused(Exception):
    """Someone paused the run; its task stops between songs."""


class CannotPause(Exception):
    pass


class BatchRunRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Reads ---

    def get(self, run_id: int) -> Optional[BatchRun]:
        return self.db.get(BatchRun, run_id)

    def active(self, kind: str) -> Optional[BatchRun]:
        return (
            self.db.query(BatchRun)
            .filter(BatchRun.kind == kind, BatchRun.status.in_(ACTIVE_STATUSES))
            .order_by(BatchRun.created_at.desc())
            .first()
        )

    def last_finished(self, kind: str) -> Optional[BatchRun]:
        return (
            self.db.query(BatchRun)
            .filter(BatchRun.kind == kind, ~BatchRun.status.in_(ACTIVE_STATUSES))
            .order_by(BatchRun.created_at.desc())
            .first()
        )

    def recent(self, limit: int, kinds: Iterable[str]) -> list[BatchRun]:
        return (
            self.db.query(BatchRun)
            .filter(BatchRun.kind.in_(list(kinds)))
            .order_by(BatchRun.created_at.desc(), BatchRun.id.desc())
            .limit(limit)
            .all()
        )

    # --- Writes from the API ---

    def create(self, kind: str, mode: str) -> BatchRun:
        now = utc_now()
        run = BatchRun(
            kind=kind,
            mode=mode,
            status="queued",
            done=0,
            failed=0,
            created_at=now,
            updated_at=now,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def record_scan(self, kind: str, *, total: int, issues: int) -> BatchRun:
        """Record a finished hand-run scan: what it looked at, what it found."""
        now = utc_now()
        run = BatchRun(
            kind=kind,
            mode="all",
            status="done",
            total=total,
            done=total,
            failed=0,
            issues=issues,
            created_at=now,
            started_at=now,
            finished_at=now,
            updated_at=now,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def set_task_id(self, run: BatchRun, task_id: str) -> None:
        run.celery_task_id = task_id
        self.db.commit()

    def interrupt_stale(self) -> int:
        """Mark running rows that stopped reporting as interrupted. Returns how many.

        Their worker died, so the next enrichment worker to start resumes them
        (resume_interrupted_runs). If the worker is alive after all, its next
        progress write marks the run running again. Runs waiting on their
        songs' own jobs are left alone: they have no task to resume, and
        refresh_handed_off keeps them current. Queued rows too: a queued run's
        message waits safely in the broker, however long the queue ahead of it.
        """
        cutoff = utc_now() - STALE_AFTER
        # A pausing run whose task went quiet has stopped one way or another.
        for run in (
            self.db.query(BatchRun)
            .filter(BatchRun.status == "pausing", BatchRun.updated_at < cutoff)
            .all()
        ):
            run.status = "paused"
        self.db.commit()
        stale = [
            run
            for run in self.db.query(BatchRun)
            .filter(BatchRun.status == "running", BatchRun.updated_at < cutoff)
            .all()
            if self.waiting_on(run) is None
        ]
        for run in stale:
            run.status = "interrupted"
            run.error = STALE_MESSAGE
        if stale:
            self.db.commit()
        return len(stale)

    def runs_to_resume(self) -> list[BatchRun]:
        """Runs whose task is gone: interrupted, or running with no worker left.

        Only call this when the enrichment worker (the one batch tasks run on)
        has just started: then no running row can still have a live task.
        Handed-off runs are skipped; their songs' jobs carry them.
        """
        rows = (
            self.db.query(BatchRun)
            .filter(BatchRun.status.in_(("running", "interrupted")))
            .order_by(BatchRun.created_at)
            .all()
        )
        return [run for run in rows if self.waiting_on(run) is None]

    def refresh_handed_off(self) -> None:
        """Bring runs waiting on their songs' own jobs up to date.

        `done` becomes how many of those jobs have finished (a finished job's
        row is gone, or no longer unfinished), and the run closes once none is
        left. Bumps `updated_at`, so a long queue never reads as a dead worker.
        """
        from app.db.models import DbJob

        running = self.db.query(BatchRun).filter(BatchRun.status == "running").all()
        changed = False
        for run in running:
            job_ids = self.waiting_on(run)
            if job_ids is None:
                continue
            waiting = (
                self.db.query(DbJob)
                .filter(
                    DbJob.id.in_(job_ids), DbJob.status.in_(_UNFINISHED_JOB_STATUSES)
                )
                .count()
            )
            run.done = max(0, (run.total or 0) - waiting)
            if waiting == 0:
                self._close(run, "done", None)
            else:
                run.updated_at = utc_now()
            changed = True
        if changed:
            self.db.commit()

    @staticmethod
    def waiting_on(run: BatchRun) -> Optional[list[str]]:
        """The job ids a handed-off run waits on; None for any other run."""
        report = run.report
        if run.status != "running" or not isinstance(report, dict):
            return None
        job_ids = report.get(WAITING_ON_KEY)
        return job_ids if isinstance(job_ids, list) else None

    def settle_pausing(self) -> int:
        """Mark every pausing run paused. Returns how many.

        Only call this when the enrichment worker has just started: a pausing
        run's task died with the old worker before it could stop itself.
        """
        rows = self.db.query(BatchRun).filter(BatchRun.status == "pausing").all()
        for run in rows:
            run.status = "paused"
            run.updated_at = utc_now()
        if rows:
            self.db.commit()
        return len(rows)

    def pause(self, run: BatchRun) -> None:
        """Pause an active run, from the API.

        A running task stops after the song it's on (the run reads "pausing"
        until then). A queued or interrupted run has no task working, so it's
        paused straight away and won't start or resume on its own. A run
        waiting on its songs' own jobs is paused by the caller, which takes
        those jobs off the queue (see pause_handed_off).
        """
        if run.status in ("pausing", "paused"):
            return
        if run.status not in ACTIVE_STATUSES:
            raise CannotPause("This run has already finished")
        run.status = "pausing" if run.status == "running" else "paused"
        run.updated_at = utc_now()
        self.db.commit()

    def pause_handed_off(self, run: BatchRun, paused_song_ids: list[str]) -> None:
        """Pause a run waiting on its songs' jobs, once the queued ones are off
        the queue. The job aligning now finishes; Resume queues the rest."""
        report = dict(run.report or {})
        report[PAUSED_SONGS_KEY] = paused_song_ids
        run.report = report
        run.status = "paused"
        run.updated_at = utc_now()
        self.db.commit()

    @staticmethod
    def paused_song_ids(run: BatchRun) -> Optional[list[str]]:
        """The songs a paused handed-off run took off the queue; None otherwise."""
        report = run.report
        if not isinstance(report, dict):
            return None
        ids = report.get(PAUSED_SONGS_KEY)
        return ids if isinstance(ids, list) else None

    def unpause(self, run: BatchRun) -> bool:
        """Resume a paused or pausing run. Returns whether it needs its task
        queued again: a pausing run's task is still on its song and carries on
        by itself; a paused one needs a new task (or, handed off, its songs
        queued again by the caller)."""
        if run.status == "pausing":
            run.status = "running"
            run.updated_at = utc_now()
            self.db.commit()
            return False
        if run.status != "paused":
            raise CannotPause("This run isn't paused")
        report = run.report
        if isinstance(report, dict) and PAUSED_SONGS_KEY in report:
            report = dict(report)
            report.pop(PAUSED_SONGS_KEY)
            run.report = report
            run.status = "running"
        else:
            run.status = "queued"
        run.updated_at = utc_now()
        self.db.commit()
        return True

    def is_pausing(self, run_id: int) -> bool:
        """Whether someone paused the run (or stopped it) since its task last looked."""
        run = self.get(run_id)
        return run is not None and run.status in ("pausing", "paused")

    def mark_paused(self, run_id: int) -> None:
        """The task stopped between songs because the run was paused."""
        run = self.get(run_id)
        if run is None or run.status not in ("pausing", "running", "paused"):
            return
        run.status = "paused"
        run.updated_at = utc_now()
        self.db.commit()

    def cancel(self, run: BatchRun) -> None:
        """Mark an active run cancelled. Its task stops before its next song."""
        self._close(run, "cancelled", None)
        self.db.commit()

    # --- Writes from the running task ---

    def start(self, run_id: int, total: int, item_ids: Optional[list] = None) -> None:
        """Begin the run from scratch, counting from zero.

        `item_ids` are the songs (or artists) it will work through, in order,
        saved so it can resume; None for a run that can only start over.
        """
        run = self._active_or_raise(run_id)
        if run.status == "paused":
            raise RunPaused(run_id)
        now = utc_now()
        run.status = "running"
        run.total = total
        run.done = 0
        run.failed = 0
        run.error = None
        run.item_ids = item_ids
        run.started_at = run.started_at or now
        run.updated_at = now
        self.db.commit()

    def resume(self, run_id: int) -> Optional[list]:
        """The ids a resumed run has left, or None when it has to start over.

        A run that saved its ids has handled the first done + failed of them,
        so it carries on after those. Marks the run running again.
        """
        run = self._active_or_raise(run_id)
        if run.status == "paused":
            raise RunPaused(run_id)
        if run.item_ids is None:
            return None
        run.status = "running"
        run.error = None
        run.updated_at = utc_now()
        self.db.commit()
        return list(run.item_ids[run.done + run.failed :])

    def interrupt(self, run_id: int) -> None:
        """The worker stopped the run between songs; it resumes on the next start."""
        run = self.get(run_id)
        if run is None or run.status not in ACTIVE_STATUSES:
            return
        # Paused by someone: it waits for Resume, not for the next worker.
        run.status = "paused" if run.status in ("pausing", "paused") else "interrupted"
        run.updated_at = utc_now()
        self.db.commit()

    def advance(self, run_id: int, *, ok: bool) -> None:
        run = self._active_or_raise(run_id)
        # A live task reporting again after its row went quiet and was marked
        # interrupted (interrupt_stale) is running after all. A pausing run
        # stays pausing: its task stops before the next song.
        if run.status in ("interrupted", "queued"):
            run.status = "running"
        run.error = None
        if ok:
            run.done += 1
        else:
            run.failed += 1
        run.updated_at = utc_now()
        self.db.commit()

    def hand_off(self, run_id: int, job_ids: list[str]) -> None:
        """The task queued one job per song and is done: the run now waits on
        those jobs, counting from zero (see refresh_handed_off)."""
        run = self._active_or_raise(run_id)
        if not job_ids:
            self._close(run, "done", None)
        else:
            run.total = len(job_ids)
            run.done = 0
            run.failed = 0
            run.report = {WAITING_ON_KEY: job_ids}
            run.updated_at = utc_now()
        self.db.commit()

    def set_report(self, run_id: int, report: dict) -> None:
        run = self.get(run_id)
        if run is None:
            return
        run.report = report
        self.db.commit()

    def finish(self, run_id: int, error: Optional[str] = None) -> None:
        run = self.get(run_id)
        if run is None or run.status not in ACTIVE_STATUSES:
            return
        self._close(run, "failed" if error else "done", error)
        self.db.commit()

    def _active_or_raise(self, run_id: int) -> BatchRun:
        run = self.get(run_id)
        if run is None or run.status not in ACTIVE_STATUSES:
            raise RunNotActive(run_id)
        return run

    @staticmethod
    def _close(run: BatchRun, status: str, error: Optional[str]) -> None:
        now = utc_now()
        run.status = status
        run.error = error
        run.finished_at = now
        run.updated_at = now
