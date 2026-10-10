"""Progress reporting from a batch task to its batch_runs row."""

from contextlib import contextmanager
from typing import Generator, Optional

from app.repositories.batch_run_repository import RunNotActive
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


class RunTracker:
    """Writes a batch task's progress to its run row, one update per song.

    Without a run id (a task started by hand or from a test) every call is a
    no-op. Progress writes never break the task: a failed write is logged and
    the work carries on. The one exception is RunNotActive, raised when
    someone cancelled the run, which stops the task between songs.
    """

    def __init__(self, run_id: Optional[int]):
        self.run_id = run_id

    def start(self, total: int) -> None:
        self._write(lambda repo: repo.start(self.run_id, total))

    def song_done(self, ok: bool = True) -> None:
        self._write(lambda repo: repo.advance(self.run_id, ok=ok))

    def finish(self, error: Optional[str] = None) -> None:
        self._write(lambda repo: repo.finish(self.run_id, error))

    def _write(self, update) -> None:
        if self.run_id is None:
            return
        from app.db.database import get_db_session
        from app.repositories.batch_run_repository import BatchRunRepository

        try:
            with get_db_session() as session:
                update(BatchRunRepository(session))
        except RunNotActive:
            raise
        except Exception:
            logger.warning(
                "batch run %s: couldn't record progress", self.run_id, exc_info=True
            )


@contextmanager
def tracked_run(run_id: Optional[int]) -> Generator[RunTracker, None, None]:
    """Close the run when the task's work ends: done, cancelled or crashed."""
    tracker = RunTracker(run_id)
    try:
        yield tracker
    except RunNotActive:
        logger.info("batch run %s was cancelled; stopping", run_id)
    except Exception as exc:
        tracker.finish(error=f"{type(exc).__name__}: {exc}")
        raise
    else:
        tracker.finish()
