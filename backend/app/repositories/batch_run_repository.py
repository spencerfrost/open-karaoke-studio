"""
Batch run repository: the record of every batch job run.
"""

from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from app.db.models import BatchRun
from sqlalchemy.orm import Session

ACTIVE_STATUSES = ("queued", "running")

# A running task reports after every song, and no song takes anywhere near
# this long. A running row this quiet belongs to a worker that died.
STALE_AFTER = timedelta(minutes=15)


def utc_now() -> datetime:
    """Now in UTC, without a zone: what the DateTime columns store and return."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RunNotActive(Exception):
    """The run was cancelled, or closed as stale, while its task still had work."""


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

    def close_stale(self) -> int:
        """Fail running rows that stopped reporting. Returns how many.

        Only running rows: a queued run's message waits safely in the broker,
        however long the queue ahead of it is.
        """
        cutoff = utc_now() - STALE_AFTER
        stale = (
            self.db.query(BatchRun)
            .filter(BatchRun.status == "running", BatchRun.updated_at < cutoff)
            .all()
        )
        for run in stale:
            self._close(
                run,
                "failed",
                "Stopped reporting progress. The worker may have crashed or restarted.",
            )
        if stale:
            self.db.commit()
        return len(stale)

    def cancel(self, run: BatchRun) -> None:
        """Mark an active run cancelled. Its task stops before its next song."""
        self._close(run, "cancelled", None)
        self.db.commit()

    # --- Writes from the running task ---

    def start(self, run_id: int, total: int) -> None:
        run = self._active_or_raise(run_id)
        now = utc_now()
        run.status = "running"
        run.total = total
        run.started_at = now
        run.updated_at = now
        self.db.commit()

    def advance(self, run_id: int, *, ok: bool) -> None:
        run = self._active_or_raise(run_id)
        if ok:
            run.done += 1
        else:
            run.failed += 1
        run.updated_at = utc_now()
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
