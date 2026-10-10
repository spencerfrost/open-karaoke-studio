"""
Admin endpoints: the overview, the background jobs page, worker status and
failed songs.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_admin
from app.db.models import User
from app.jobs.celery_app import celery
from app.repositories.batch_run_repository import BatchRunRepository
from app.repositories.song_repository import SongRepository
from app.schemas.song import SongResponse
from app.services.admin_overview import build_overview
from app.services.batch_jobs import (
    JOBS,
    UnknownJob,
    UnsupportedMode,
    get_job,
    job_summary,
    serialize_run,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])

# The queues run_celery.sh starts a worker for. A queue no worker answers for
# means its jobs sit waiting.
EXPECTED_QUEUES = ("audio", "enrichment", "lyrics")
WORKER_PING_TIMEOUT_SECONDS = 1.0


@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Counts for the admin landing page: what needs reviewing, job coverage
    and runs in progress, songs added per week, and each hand-run scan's last
    result. Cheap enough to poll; nothing here scans the library."""
    return build_overview(db)


@router.get("/jobs")
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Every batch job: what it covers, how many each mode would run on, its
    last finished run and any run queued or in progress."""
    repo = BatchRunRepository(db)
    repo.close_stale()
    jobs = []
    for job in JOBS.values():
        jobs.append(
            {
                "kind": job.kind,
                "modes": list(job.modes),
                **job_summary(db, job),
                "lastRun": serialize_run(repo.last_finished(job.kind)),
                "activeRun": serialize_run(repo.active(job.kind)),
            }
        )
    return {"jobs": jobs}


@router.get("/jobs/runs")
def list_runs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Recent runs of every job, newest first."""
    return {
        "runs": [
            serialize_run(run)
            for run in BatchRunRepository(db).recent(limit, kinds=JOBS.keys())
        ]
    }


@router.post("/jobs/{kind}/run", status_code=202)
def run_job(
    kind: str,
    mode: str = Query("missing"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Queue a run of a batch job. One run per job at a time."""
    try:
        job = get_job(kind, mode)
    except UnknownJob:
        raise HTTPException(status_code=404, detail=f"No batch job called {kind}")
    except UnsupportedMode as e:
        raise HTTPException(status_code=400, detail=str(e))

    repo = BatchRunRepository(db)
    repo.close_stale()
    if repo.active(kind) is not None:
        raise HTTPException(status_code=409, detail="This job is already running")

    run = repo.create(kind, mode)
    try:
        task = celery.send_task(job.task_name, kwargs={"mode": mode, "run_id": run.id})
    except Exception as e:
        logger.error("Couldn't queue batch job %s: %s", kind, e, exc_info=True)
        repo.finish(run.id, error=f"Couldn't queue the job: {e}")
        raise HTTPException(status_code=503, detail="Couldn't reach the job queue")
    repo.set_task_id(run, task.id)
    logger.info(
        "Queued batch job %s (mode=%s) as run %s, task %s", kind, mode, run.id, task.id
    )
    return {"run": serialize_run(run)}


@router.post("/jobs/runs/{run_id}/cancel")
def cancel_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Stop a queued or running run. A running one stops before its next song."""
    repo = BatchRunRepository(db)
    run = repo.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="No such run")
    if run.status not in ("queued", "running"):
        raise HTTPException(status_code=409, detail="This run has already finished")

    repo.cancel(run)
    if run.celery_task_id:
        # Drops it if it hasn't started. A started task notices the
        # cancelled row itself, so there's no need to kill the worker.
        try:
            celery.control.revoke(run.celery_task_id)
        except Exception:
            logger.warning("Couldn't revoke task %s", run.celery_task_id, exc_info=True)
    logger.info("Cancelled batch run %s (%s)", run.id, run.kind)
    return {"run": serialize_run(run)}


@router.get("/workers")
def worker_status(current_user: User = Depends(require_admin)):
    """Which Celery workers answer, and which queues have nobody serving them.

    Sync on purpose: the broadcast blocks for its whole timeout, so FastAPI
    runs it in a thread instead of stalling the event loop.
    """
    try:
        replies = (
            celery.control.inspect(timeout=WORKER_PING_TIMEOUT_SECONDS).active_queues()
            or {}
        )
    except Exception as e:
        logger.warning("Couldn't reach Celery workers: %s", e)
        return {"brokerReachable": False, "workers": [], "queues": []}

    workers = sorted(replies)
    queues = []
    for queue in EXPECTED_QUEUES:
        serving = [
            worker
            for worker, worker_queues in replies.items()
            if any(q.get("name") == queue for q in worker_queues or [])
        ]
        queues.append({"queue": queue, "workers": sorted(serving)})
    return {"brokerReachable": True, "workers": workers, "queues": queues}


@router.get("/songs/failed", response_model=List[SongResponse])
def list_failed_songs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Songs whose download or processing failed, most recent first, with
    the reason (`errorMessage`) and when (`failedAt`). The songbook hides
    them."""
    return [song.to_dict() for song in SongRepository(db).fetch_failed()]
