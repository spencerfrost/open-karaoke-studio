"""
Batch runs - one row per run of a library-wide maintenance job.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from .base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BatchRun(Base):
    """One run of a batch job (loudness, album art, lyrics alignment...).

    The API creates the row as "queued" when someone presses Run, so the
    admin page shows it straight away; the task moves it to "running",
    counts songs as it goes and closes it as "done" or "failed".
    """

    __tablename__ = "batch_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Which job: a key of app.services.batch_jobs.JOBS.
    kind = Column(String, nullable=False, index=True)
    # "missing", "all", or a job's own mode (alignment has "repair").
    mode = Column(String, nullable=False)
    # "queued" | "running" | "done" | "failed"
    status = Column(String, nullable=False, default="queued", index=True)
    celery_task_id = Column(String, nullable=True)

    # Songs (or artists) the run picked up. None until the task has looked.
    total = Column(Integer, nullable=True)
    # Handled without an error, including ones there was nothing to find for.
    done = Column(Integer, nullable=False, default=0)
    # Hit an error.
    failed = Column(Integer, nullable=False, default=0)
    # Why the whole run stopped, when it did.
    error = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=_now)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    # Bumped on every progress update; a running row that stops changing
    # belongs to a worker that died.
    updated_at = Column(DateTime, nullable=False, default=_now)
