"""
Admin endpoints: the overview, the background jobs page, worker status,
failed songs, the Compare breaks page, the Compare word timing page and the
Check vocal range page.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_admin
from app.db.models import DbSong, User
from app.jobs.celery_app import celery
from app.repositories.batch_run_repository import (
    ACTIVE_STATUSES,
    BatchRunRepository,
)
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

# The queues celery_workers.sh starts a worker for. A queue no worker answers
# for means its jobs sit waiting.
EXPECTED_QUEUES = ("audio", "enrichment", "lyrics", "lyrics_backfill")
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
    repo.refresh_handed_off()
    repo.interrupt_stale()
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
    repo = BatchRunRepository(db)
    repo.refresh_handed_off()
    return {
        "runs": [serialize_run(run) for run in repo.recent(limit, kinds=JOBS.keys())]
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
    repo.interrupt_stale()
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


@router.get("/jobs/runs/{run_id}/report")
def run_report(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """The report a run wrote (the artist credits rebuild writes one)."""
    run = BatchRunRepository(db).get(run_id)
    if run is None or run.report is None:
        raise HTTPException(status_code=404, detail="This run has no report")
    return {"run": serialize_run(run), "report": run.report}


@router.post("/jobs/runs/{run_id}/cancel")
def cancel_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Stop an active run (queued, running or interrupted). A running one stops
    before its next song; an interrupted one won't resume;
    one waiting on its songs' own jobs takes the ones still queued off the
    queue, and the one aligning now finishes."""
    from app.jobs.lyrics_dispatch import cancel_queued_alignments

    repo = BatchRunRepository(db)
    run = repo.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="No such run")
    if run.status not in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="This run has already finished")

    waiting_on = repo.waiting_on(run)
    repo.cancel(run)
    if waiting_on:
        cancel_queued_alignments(waiting_on)
    if run.celery_task_id:
        # Drops it if it hasn't started. A started task notices the
        # cancelled row itself, so there's no need to kill the worker.
        try:
            celery.control.revoke(run.celery_task_id)
        except Exception:
            logger.warning("Couldn't revoke task %s", run.celery_task_id, exc_info=True)
    logger.info("Cancelled batch run %s (%s)", run.id, run.kind)
    return {"run": serialize_run(run)}


@router.post("/jobs/runs/{run_id}/pause")
def pause_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Pause an active run, to free the GPU. A running one stops after the song
    it's on and gives back its GPU memory; one waiting on its songs' own jobs
    takes the queued ones off the queue, and the one aligning now finishes. A
    paused run stays paused, even across worker restarts, until Resume."""
    from app.jobs.lyrics_dispatch import take_queued_alignments_off

    repo = BatchRunRepository(db)
    run = repo.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="No such run")
    if run.status not in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="This run has already finished")

    waiting_on = repo.waiting_on(run)
    if waiting_on is not None:
        repo.pause_handed_off(run, take_queued_alignments_off(waiting_on))
        try:
            celery.send_task(
                "release_gpu_memory", kwargs={"reason": f"batch run {run.id} paused"}
            )
        except Exception:
            logger.warning("Couldn't queue the GPU memory release", exc_info=True)
    else:
        was_queued = run.status == "queued"
        repo.pause(run)
        if was_queued and run.celery_task_id:
            # Not started: drop it, and Resume queues a new one. One that
            # starts anyway sees the paused row and stops.
            try:
                celery.control.revoke(run.celery_task_id)
            except Exception:
                logger.warning(
                    "Couldn't revoke task %s", run.celery_task_id, exc_info=True
                )
    logger.info("Paused batch run %s (%s)", run.id, run.kind)
    return {"run": serialize_run(run)}


@router.post("/jobs/runs/{run_id}/resume")
def resume_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Carry on a paused run from where it stopped."""
    from app.jobs.lyrics_dispatch import enqueue_song_alignment
    from app.repositories.batch_run_repository import CannotPause

    repo = BatchRunRepository(db)
    run = repo.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="No such run")
    job = JOBS.get(run.kind)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No batch job called {run.kind}")

    paused_songs = repo.paused_song_ids(run) if run.status == "paused" else None
    try:
        needs_task = repo.unpause(run)
    except CannotPause as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not needs_task:
        return {"run": serialize_run(run)}

    if paused_songs is not None:
        # A handed-off run: queue its songs' jobs again, under the same job
        # ids it's waiting on.
        for song in db.query(DbSong).filter(DbSong.id.in_(paused_songs)).all():
            enqueue_song_alignment(
                song, include_remote=run.mode != "retime", background=True
            )
    else:
        try:
            task = celery.send_task(
                job.task_name, kwargs={"mode": run.mode, "run_id": run.id}
            )
        except Exception as e:
            logger.error("Couldn't queue batch run %s: %s", run.id, e, exc_info=True)
            repo.pause(run)
            raise HTTPException(status_code=503, detail="Couldn't reach the job queue")
        repo.set_task_id(run, task.id)
    logger.info("Resumed batch run %s (%s)", run.id, run.kind)
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


# ---------------------------------------------------------------------------
# Compare breaks: instrumental breaks from the singing map vs from word gaps
# ---------------------------------------------------------------------------


@router.get("/singing-map/songs")
def list_singing_map_songs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Every processed song with synced lyrics (no lyrics, no bars), with how
    many breaks each method finds, how many they disagree on and how many
    moments are still to check, plus a tally of every answer so far. Songs
    with the most still to check come first, songs not measured yet last."""
    from app.repositories.break_check_repository import BreakCheckRepository
    from app.services.singing_map_review import summarize, tally

    songs = (
        db.query(DbSong)
        .filter(DbSong.status == "processed", DbSong.synced_lyrics.isnot(None))
        .all()
    )
    answers = BreakCheckRepository(db).all_answers()
    rows = [summarize(song, answers.get(song.id, {})) for song in songs]
    rows.sort(
        key=lambda r: (
            r["disagreements"] is None,
            r["toCheck"] == 0,
            -(r["disagreements"] or 0),
            r["title"].lower(),
        )
    )
    return {"songs": rows, "tally": tally(rows)}


@router.get("/singing-map/songs/{song_id}")
def get_singing_map_song(
    song_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """One song's singing map, its lyric lines, both sets of breaks and the
    moments worth a listen. A song with no map yet is measured now (a second
    or two) and the map saved."""
    from app.jobs.metadata_tasks import detect_and_store_singing_map
    from app.repositories.break_check_repository import BreakCheckRepository
    from app.services.singing_map_review import detail

    song = SongRepository(db).fetch(song_id)
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    if song.singing_map is None:
        outcome = detect_and_store_singing_map(song_id)
        if outcome != "ok":
            raise HTTPException(
                status_code=409,
                detail=(
                    "This song has no vocals track to measure"
                    if outcome == "no_audio"
                    else "Measuring this song failed; see the API log"
                ),
            )
        db.expire(song)
    return detail(song, BreakCheckRepository(db).answers_for_song(song_id))


class BreakCheckAnswer(BaseModel):
    key: str
    # None clears the answer.
    answer: Optional[str] = None


class BreakCheckAnswers(BaseModel):
    answers: List[BreakCheckAnswer]


@router.put("/singing-map/songs/{song_id}/checks")
def save_singing_map_checks(
    song_id: str,
    body: BreakCheckAnswers,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Answer moments by ear: whether the map or today's bar was right. Each
    item names a moment by its `key` from the song's moments; `answer` null
    clears it. All or nothing: a key the song no longer shows, or an answer
    that doesn't fit its moment, is a 400 and saves nothing. Returns the song
    as GET does."""
    from app.repositories.break_check_repository import BreakCheckRepository
    from app.services.singing_map_review import BadAnswer, detail, save_answers

    song = SongRepository(db).fetch(song_id)
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    try:
        save_answers(
            db, song, [item.model_dump() for item in body.answers], current_user.id
        )
    except BadAnswer as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    logger.info("Break checks for song %s: %d answer(s)", song_id, len(body.answers))
    return detail(song, BreakCheckRepository(db).answers_for_song(song_id))


# ---------------------------------------------------------------------------
# Compare word timing: two experimental alignments of the same songs, by ear
# ---------------------------------------------------------------------------


@router.get("/word-timing/experiments")
def list_word_timing_experiments(
    db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Experiments found in the experiments folder, newest name last (the
    folder exists only on the machine that ran them), then the LRC offset
    sweep's shifts waiting to be applied, from the database."""
    from app.services.word_timing_experiments import list_experiments

    return {"experiments": list_experiments(db)}


@router.get("/word-timing/experiments/{experiment_id}/songs")
def list_word_timing_songs(
    experiment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """The experiment's songs, each with how many lines differ between its two
    timings and how many of those are answered, plus a tally of answers."""
    from app.services.word_timing_experiments import NotFound, list_songs

    try:
        return list_songs(experiment_id, db)
    except NotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/word-timing/experiments/{experiment_id}/songs/{song_id}")
def get_word_timing_song(
    experiment_id: str,
    song_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """One song's moments: each line whose two timings differ, with both sets
    of words and any answer given."""
    from app.services.word_timing_experiments import NotFound, song_detail

    try:
        return song_detail(experiment_id, song_id, db)
    except NotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


class WordTimingAnswer(BaseModel):
    key: str
    # "b_right", "a_right", "both_wrong" or "cant_tell"; None clears it.
    answer: Optional[str] = None


class WordTimingAnswers(BaseModel):
    answers: List[WordTimingAnswer]


@router.put("/word-timing/experiments/{experiment_id}/songs/{song_id}/answers")
def save_word_timing_answers(
    experiment_id: str,
    song_id: str,
    body: WordTimingAnswers,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Say which timing followed the singing, by moment key. All or nothing:
    an unknown key or answer is a 400 and saves nothing. Returns the song as
    GET does."""
    from app.services.word_timing_experiments import (
        BadAnswer,
        NotFound,
        save_answers,
        song_detail,
    )

    try:
        save_answers(
            experiment_id, song_id, [item.model_dump() for item in body.answers], db
        )
        return song_detail(experiment_id, song_id, db)
    except NotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except BadAnswer as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


# ---------------------------------------------------------------------------
# Check vocal range: the vocal range benchmark's moments, by ear
# ---------------------------------------------------------------------------


def _method_list(methods: Optional[str]) -> Optional[List[str]]:
    """`?methods=a,b` -> ["a", "b"]; absent means every method."""
    if methods is None:
        return None
    return [m for m in methods.split(",") if m]


@router.get("/vocal-range/songs")
def list_vocal_range_songs(
    methods: Optional[str] = Query(None, description="Comma-separated method names"),
    current_user: User = Depends(require_admin),
):
    """The benchmark's test songs with each method's range and how many of
    their primary moments are answered, plus each method's verdicts so far.
    `methods` narrows it to those methods. Empty where the benchmark wasn't
    run: its results exist only on that machine."""
    from app.services.vocal_range_review import list_songs

    return list_songs(_method_list(methods))


@router.get("/vocal-range/songs/{song_id}")
def get_vocal_range_song(
    song_id: str,
    methods: Optional[str] = Query(None, description="Comma-separated method names"),
    current_user: User = Depends(require_admin),
):
    """One test song: each method's range, its sheet-music reference, and the
    moments that set each end, with the pitch track around each."""
    from app.services.vocal_range_review import NotFound, song_detail

    try:
        return song_detail(song_id, _method_list(methods))
    except NotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


class VocalRangeAnswer(BaseModel):
    # A moment's key, or "kind" for what kind of song it is.
    key: str
    # None clears it.
    answer: Optional[str] = None


class VocalRangeAnswers(BaseModel):
    answers: List[VocalRangeAnswer]
    # The methods the page shows, so the reply matches its GET.
    methods: Optional[List[str]] = None


@router.put("/vocal-range/songs/{song_id}/answers")
def save_vocal_range_answers(
    song_id: str,
    body: VocalRangeAnswers,
    current_user: User = Depends(require_admin),
):
    """Answer moments by ear (is this the note the lead sings here?) and the
    song's kind. All or nothing: an unknown key or answer is a 400 and saves
    nothing. Returns the song as GET does."""
    from app.services.vocal_range_review import (
        BadAnswer,
        NotFound,
        save_answers,
        song_detail,
    )

    try:
        save_answers(song_id, [item.model_dump() for item in body.answers])
        return song_detail(song_id, body.methods)
    except NotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except BadAnswer as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
