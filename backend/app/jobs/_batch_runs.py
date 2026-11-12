"""Progress reporting from a batch task to its batch_runs row, and resuming it.

A batch task works through a whole library in one Celery task. Two things
make that safe to stop:

- Between songs, the task checks whether its worker is shutting down, and if
  so stops there and marks its run interrupted. Without this, a shutdown waits
  for every song left: the thread pool can't stop a running task.
- The run saves the ids it works through when it starts. When the enrichment
  worker starts again, resume_interrupted_runs queues the task again for every
  run that was interrupted or whose worker died, and the task carries on after
  the songs it had already handled.

Pausing uses the same two pieces. Pause marks the run "pausing"; between
songs the task sees it, marks it "paused", gives back its GPU memory and
returns. Resume queues the task again, and it carries on from the saved ids.
A paused run stays paused across worker restarts.
"""

from contextlib import contextmanager
from typing import Any, Callable, Generator, Iterable, Iterator, Optional, TypeVar

from celery.utils.log import get_task_logger

from app.repositories.batch_run_repository import RunNotActive, RunPaused

logger = get_task_logger(__name__)

# Batch tasks are routed here (task_routes in celery_app); only the worker
# consuming it can have been running them.
BATCH_QUEUE = "enrichment"

T = TypeVar("T")


class WorkerStopping(Exception):
    """The worker is shutting down; the run stops between songs."""


def worker_stopping() -> bool:
    """Whether this worker has started a warm or cold shutdown.

    Celery sets these from its signal handlers. A warm shutdown sets
    should_stop to the exit code, 0, so test against None and False.
    """
    from celery.worker import state

    return any(
        flag is not None and flag is not False
        for flag in (state.should_stop, state.should_terminate)
    )


class RunTracker:
    """Writes a batch task's progress to its run row, one update per song.

    Without a run id (a task started by hand or from a test) every call is a
    no-op. Progress writes never break the task: a failed write is logged and
    the work carries on. The one exception is RunNotActive, raised when
    someone cancelled the run, which stops the task between songs.
    """

    def __init__(self, run_id: Optional[int]):
        self.run_id = run_id
        self.handed_off = False

    def begin(self, select: Callable[[], list]) -> list:
        """The ids this run works through, starting the run.

        A fresh run takes `select()` and saves it; a resumed one gets the ids
        it had left. Use with `each`, which reports one id per song.
        """
        if self.run_id is not None:
            remaining = self._write(lambda repo: repo.resume(self.run_id))
            if remaining is not None:
                logger.info(
                    "batch run %s: resuming with %d left", self.run_id, len(remaining)
                )
                return remaining
        ids = select()
        self._write(lambda repo: repo.start(self.run_id, len(ids), item_ids=ids))
        return ids

    def each(self, ids: Iterable[T]) -> Iterator[T]:
        """Yield ids until the worker starts shutting down.

        The task must call song_done once for every id it's given: a resumed
        run carries on after done + failed of its saved ids.
        """
        for item in ids:
            if worker_stopping():
                raise WorkerStopping()
            if self._write(lambda repo: repo.is_pausing(self.run_id)):
                raise RunPaused(self.run_id)
            yield item

    def start(self, total: int) -> None:
        """Begin a run that can only start over (it saves no ids to resume from)."""
        self._write(lambda repo: repo.start(self.run_id, total))

    def song_done(self, ok: bool = True) -> None:
        self._write(lambda repo: repo.advance(self.run_id, ok=ok))

    def hand_off(self, job_ids: list[str]) -> None:
        """Leave the run open, waiting on these jobs, when the task returns."""
        self.handed_off = True
        self._write(lambda repo: repo.hand_off(self.run_id, job_ids))

    def report(self, report: dict) -> None:
        self._write(lambda repo: repo.set_report(self.run_id, report))

    def pause(self) -> None:
        """Mark the run paused and give back the GPU memory its songs used."""
        from app.services.gpu_idle_cleanup import release_gpu_memory_now

        self._write(lambda repo: repo.mark_paused(self.run_id))
        try:
            release_gpu_memory_now(f"batch run {self.run_id} paused")
        except Exception:
            logger.warning("Couldn't release GPU memory", exc_info=True)

    def interrupt(self) -> None:
        self._write(lambda repo: repo.interrupt(self.run_id))

    def finish(self, error: Optional[str] = None) -> None:
        self._write(lambda repo: repo.finish(self.run_id, error))

    def _write(self, update: Callable[[Any], Any]) -> Any:
        """Run one repository call; its result, or None when it couldn't."""
        if self.run_id is None:
            return None
        from app.db.database import get_db_session
        from app.repositories.batch_run_repository import BatchRunRepository

        try:
            with get_db_session() as session:
                return update(BatchRunRepository(session))
        except (RunNotActive, RunPaused):
            raise
        except Exception:
            logger.warning(
                "batch run %s: couldn't record progress", self.run_id, exc_info=True
            )
            return None


@contextmanager
def tracked_run(run_id: Optional[int]) -> Generator[RunTracker, None, None]:
    """Close the run when the task's work ends: done, cancelled, stopped or crashed."""
    tracker = RunTracker(run_id)
    try:
        yield tracker
    except RunNotActive:
        logger.info("batch run %s was cancelled; stopping", run_id)
    except RunPaused:
        logger.info("batch run %s was paused; stopping", run_id)
        tracker.pause()
    except WorkerStopping:
        logger.info("batch run %s: worker shutting down; stopping", run_id)
        tracker.interrupt()
    except Exception as exc:
        tracker.finish(error=f"{type(exc).__name__}: {exc}")
        raise
    else:
        if not tracker.handed_off:
            tracker.finish()


def resume_interrupted_runs(queues: Iterable[str]) -> int:
    """Queue the task again for every run left without one. Returns how many.

    Called when a worker starts. Only the worker consuming BATCH_QUEUE can have
    been running batch tasks, and it just started, so any run still marked
    running lost its task. This assumes one such worker: a second one running
    alongside would see the first one's runs as orphaned.
    """
    if BATCH_QUEUE not in set(queues):
        return 0

    from app.db.database import get_db_session
    from app.jobs.celery_app import celery
    from app.repositories.batch_run_repository import BatchRunRepository
    from app.services.batch_jobs import JOBS

    resumed = 0
    with get_db_session() as session:
        repo = BatchRunRepository(session)
        repo.settle_pausing()
        for run in repo.runs_to_resume():
            job = JOBS.get(run.kind)
            if job is None:
                continue
            repo.interrupt(run.id)
            task = celery.send_task(
                job.task_name, kwargs={"mode": run.mode, "run_id": run.id}
            )
            repo.set_task_id(run, task.id)
            logger.info(
                "Resuming batch run %s (%s, %d of %s handled)",
                run.id,
                run.kind,
                run.done + run.failed,
                run.total,
            )
            resumed += 1
    return resumed
