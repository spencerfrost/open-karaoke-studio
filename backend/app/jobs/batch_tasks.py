"""Batch Celery tasks for library-wide backfills and alignment.

Each task takes the mode it runs in and the id of the batch_runs row the API
created for it, and reports its progress there after every song. Which songs a
mode selects is defined once, in app.services.batch_jobs.

The song-by-song tasks take their ids from run.begin and loop over run.each,
which is what lets a worker shutdown stop them between songs and a restarted
worker resume them (see _batch_runs).
"""

from typing import Optional

from celery.utils.log import get_task_logger

from ._batch_runs import tracked_run
from .celery_app import celery

logger = get_task_logger(__name__)

# Spacing between album lookups. Deezer allows 10 requests a second and
# YouTube Music publishes no limit; a second keeps both comfortable.
ALBUM_LOOKUP_GAP_SECONDS = 1.0


def _select(kind: str, mode: str) -> list:
    from app.db.database import get_db_session
    from app.services.batch_jobs import select_ids

    with get_db_session() as session:
        return select_ids(session, kind, mode)


@celery.task(name="batch_fingerprint_songs")
def batch_fingerprint_songs(
    mode: str = "missing", run_id: Optional[int] = None
) -> dict:
    """Batch task: fingerprint songs via AcoustID.

    "missing" takes songs never checked; "retry" takes unconfirmed songs AcoustID
    couldn't settle (ambiguous, no match, or a failed lookup).
    """
    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.acoustid_service import AcoustIdService

    config = get_config()
    counts = {"ok": 0, "no_audio": 0, "error": 0}

    with tracked_run(run_id) as run:
        song_ids = run.begin(lambda: _select("fingerprint", mode))
        logger.info(
            "batch_fingerprint_songs: processing %d songs (mode=%s)",
            len(song_ids),
            mode,
        )

        for song_id in run.each(song_ids):
            song_dir = config.BASE_LIBRARY_DIR / song_id
            original_path = song_dir / "original.mp3"
            instrumental_path = song_dir / "instrumental.mp3"
            vocals_path = song_dir / "vocals.mp3"
            audio_path = (
                original_path
                if original_path.exists()
                else instrumental_path if instrumental_path.exists() else vocals_path
            )

            if not audio_path.exists():
                logger.warning(
                    "batch_fingerprint_songs: no audio for song %s, skipping", song_id
                )
                with get_db_session() as session:
                    SongRepository(session).update(
                        song_id, acoustid_fingerprint_status="failed"
                    )
                counts["no_audio"] += 1
                run.song_done()
                continue

            try:
                with get_db_session() as session:
                    outcome = AcoustIdService(
                        SongRepository(session)
                    ).fingerprint_and_link(song_id, audio_path)
                # Credits follow the linked recording, as for a single song.
                if outcome == "matched":
                    celery.send_task("enrich_song_artist_credits", args=[song_id])
                counts["ok"] += 1
                run.song_done()
            except Exception:
                logger.warning(
                    "batch_fingerprint_songs: error processing song %s",
                    song_id,
                    exc_info=True,
                )
                counts["error"] += 1
                run.song_done(ok=False)

    logger.info("batch_fingerprint_songs: done — %s", counts)
    return counts


@celery.task(name="batch_fetch_albums")
def batch_fetch_albums(mode: str = "missing", run_id: Optional[int] = None) -> dict:
    """Batch task: find each song's album and cover (YouTube Music, then Deezer).

    "all" looks every song up again. Songs whose album a person set are never
    included. When the run ends, albums no song links to are deleted.
    """
    import time

    from app.services.album_service import delete_unlinked_albums, refresh_song_album

    counts = {"found": 0, "no_cover": 0, "not_found": 0, "hand_set": 0, "error": 0}

    with tracked_run(run_id) as run:
        song_ids = run.begin(lambda: _select("song_albums", mode))
        logger.info(
            "batch_fetch_albums: processing %d songs (mode=%s)", len(song_ids), mode
        )

        for i, song_id in enumerate(run.each(song_ids)):
            if i > 0:
                time.sleep(ALBUM_LOOKUP_GAP_SECONDS)
            try:
                outcome = refresh_song_album(song_id)
            except Exception:
                logger.warning(
                    "batch_fetch_albums: error for song %s", song_id, exc_info=True
                )
                outcome = "error"
            counts[outcome] = counts.get(outcome, 0) + 1
            run.song_done(ok=outcome != "error")

        counts["albums_deleted"] = delete_unlinked_albums()

    logger.info("batch_fetch_albums: done — %s", counts)
    return counts


@celery.task(name="batch_backfill_duration")
def batch_backfill_duration(
    mode: str = "missing", run_id: Optional[int] = None
) -> dict:
    """Batch task: populate duration from original audio file."""
    from pathlib import Path

    import librosa

    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    config = get_config()
    success = 0
    skipped = 0

    with tracked_run(run_id) as run:
        song_ids = run.begin(lambda: _select("duration", mode))
        logger.info(
            "batch_backfill_duration: processing %d songs (mode=%s)",
            len(song_ids),
            mode,
        )

        for song_id in run.each(song_ids):
            audio_path = Path(config.BASE_LIBRARY_DIR) / song_id / "original.mp3"
            if not audio_path.exists():
                skipped += 1
                run.song_done()
                continue
            try:
                duration = librosa.get_duration(path=str(audio_path))
                with get_db_session() as session:
                    SongRepository(session).update(song_id, duration=duration)
                success += 1
                run.song_done()
            except Exception:
                logger.warning(
                    "batch_backfill_duration: error for song %s", song_id, exc_info=True
                )
                skipped += 1
                run.song_done(ok=False)

    logger.info(
        "batch_backfill_duration: done — %d updated, %d skipped", success, skipped
    )
    return {"processed": success + skipped, "success": success, "skipped": skipped}


@celery.task(name="batch_backfill_vocal_range")
def batch_backfill_vocal_range(
    mode: str = "missing", run_id: Optional[int] = None
) -> dict:
    """Batch task: detect vocal range from each song's vocals stem.

    Runs songs one after another inside this single task (~10-30s each) rather
    than fanning out per-song tasks, so a long backfill occupies one enrichment
    slot and new downloads can still post-process alongside it. Each song is
    saved as it finishes, so re-running with mode="missing" resumes.
    """
    from .metadata_tasks import detect_and_store_vocal_range

    counts = {"ok": 0, "no_range": 0, "no_audio": 0, "error": 0}

    with tracked_run(run_id) as run:
        song_ids = run.begin(lambda: _select("vocal_range", mode))
        logger.info(
            "batch_backfill_vocal_range: processing %d songs (mode=%s)",
            len(song_ids),
            mode,
        )

        for i, song_id in enumerate(run.each(song_ids), 1):
            outcome = detect_and_store_vocal_range(song_id)
            counts[outcome] += 1
            run.song_done(ok=outcome != "error")
            if i % 25 == 0:
                logger.info(
                    "batch_backfill_vocal_range: %d/%d done %s",
                    i,
                    len(song_ids),
                    counts,
                )

    logger.info("batch_backfill_vocal_range: done — %s", counts)
    return {
        "processed": sum(counts.values()),
        "success": counts["ok"],
        "skipped": counts["no_range"] + counts["no_audio"] + counts["error"],
        **counts,
    }


@celery.task(name="batch_backfill_loudness")
def batch_backfill_loudness(
    mode: str = "missing", run_id: Optional[int] = None
) -> dict:
    """Batch task: measure each song's loudness from its stems and store its gain.

    Runs songs one after another inside this single task (a second or two each)
    rather than fanning out per-song tasks, so new downloads can still
    post-process alongside it. Each song is saved as it finishes, so re-running
    with mode="missing" resumes.
    """
    from .metadata_tasks import detect_and_store_loudness

    counts = {"ok": 0, "silent": 0, "no_audio": 0, "error": 0}

    with tracked_run(run_id) as run:
        song_ids = run.begin(lambda: _select("loudness", mode))
        logger.info(
            "batch_backfill_loudness: processing %d songs (mode=%s)",
            len(song_ids),
            mode,
        )

        for i, song_id in enumerate(run.each(song_ids), 1):
            outcome = detect_and_store_loudness(song_id)
            counts[outcome] += 1
            run.song_done(ok=outcome != "error")
            if i % 25 == 0:
                logger.info(
                    "batch_backfill_loudness: %d/%d done %s", i, len(song_ids), counts
                )

    logger.info("batch_backfill_loudness: done — %s", counts)
    return {
        "processed": sum(counts.values()),
        "success": counts["ok"],
        "skipped": counts["silent"] + counts["no_audio"] + counts["error"],
        **counts,
    }


@celery.task(name="batch_backfill_singing_map")
def batch_backfill_singing_map(
    mode: str = "missing", run_id: Optional[int] = None
) -> dict:
    """Batch task: measure when each song's lead and backing vocals are singing.

    One song after another inside this task (a second or two each), like the
    loudness backfill. Each map is saved as it finishes, so re-running with
    mode="missing" resumes; mode="all" re-measures after a threshold change.
    """
    from .metadata_tasks import detect_and_store_singing_map

    counts = {"ok": 0, "no_audio": 0, "error": 0}

    with tracked_run(run_id) as run:
        song_ids = run.begin(lambda: _select("singing_map", mode))
        logger.info(
            "batch_backfill_singing_map: processing %d songs (mode=%s)",
            len(song_ids),
            mode,
        )

        for i, song_id in enumerate(run.each(song_ids), 1):
            outcome = detect_and_store_singing_map(song_id)
            counts[outcome] += 1
            run.song_done(ok=outcome != "error")
            if i % 25 == 0:
                logger.info(
                    "batch_backfill_singing_map: %d/%d done %s",
                    i,
                    len(song_ids),
                    counts,
                )

    logger.info("batch_backfill_singing_map: done — %s", counts)
    return {
        "processed": sum(counts.values()),
        "success": counts["ok"],
        "skipped": counts["no_audio"] + counts["error"],
        **counts,
    }


@celery.task(name="batch_fetch_artist_images")
def batch_fetch_artist_images(
    mode: str = "missing", run_id: Optional[int] = None
) -> dict:
    """Batch task: fetch a Discogs image for every artist not checked yet.

    One artist at a time, to stay inside Discogs' rate limit.
    """
    import asyncio

    from app.db.database import SessionLocal
    from app.services.artist_image_service import ArtistImageService
    from app.services.file_service import FileService

    counts = {"fetched": 0, "not_found": 0, "errors": 0}

    with tracked_run(run_id) as run:
        artist_ids = run.begin(lambda: _select("artist_images", mode))
        logger.info("batch_fetch_artist_images: processing %d artists", len(artist_ids))

        service = ArtistImageService(FileService(), SessionLocal)
        for artist_id in run.each(artist_ids):
            try:
                path = asyncio.run(service.get_or_fetch_artist_image(artist_id))
                counts["fetched" if path is not None else "not_found"] += 1
                run.song_done()
            except Exception:
                logger.warning(
                    "batch_fetch_artist_images: error for artist %s",
                    artist_id,
                    exc_info=True,
                )
                counts["errors"] += 1
                run.song_done(ok=False)

    logger.info("batch_fetch_artist_images: done — %s", counts)
    return counts


@celery.task(name="batch_align_lyrics")
def batch_align_lyrics(mode: str = "missing", run_id: Optional[int] = None) -> dict:
    """Batch task: queue align_song_lyrics for every song a `mode` run selects.

    Each song runs as its own job on the low-priority lyrics_backfill queue, so
    new songs and fixes people ask for go first. Otherwise it's exactly like a
    new song's alignment: in its own language, with remote candidates, the offset
    sweep and ASR re-timing, and respecting hand-picked and rejected lyrics.
    While queuing, the run counts songs queued. Then it hands off to the
    queued jobs and stays running, counting them as they finish, until the
    last one does (BatchRunRepository.refresh_handed_off). A song already
    aligning isn't queued again and isn't waited on.
    """
    from app.db.database import get_db_session
    from app.jobs.lyrics_dispatch import enqueue_song_alignment
    from app.services.lyrics_repair import count_reasons, select_songs_for_alignment

    selected: list = []
    with_vocals = 0
    reason_counts: dict = {}
    results: list = []
    queued = 0
    queued_job_ids: list[str] = []

    with tracked_run(run_id) as run:
        with get_db_session() as session:
            selected, with_vocals = select_songs_for_alignment(session, mode)
            reason_counts = count_reasons(selected)
            run.start(len(selected))
            for song, reasons in selected:
                dispatch = enqueue_song_alignment(
                    song, include_remote=True, background=True
                )
                queued += int(dispatch["dispatched"])
                if dispatch["dispatched"]:
                    queued_job_ids.append(dispatch["jobId"])
                run.song_done()
                results.append(
                    {
                        "songId": song.id,
                        "title": f"{song.artist or '?'} — {song.title or song.id}",
                        "status": (
                            "queued" if dispatch["dispatched"] else "already_running"
                        ),
                        "reasons": reasons,
                    }
                )
            run.hand_off(queued_job_ids)

    logger.info(
        "batch_align_lyrics: mode=%s, queued %d of %d selected songs (%d with vocals), reasons=%s",
        mode,
        queued,
        len(selected),
        with_vocals,
        reason_counts,
    )
    return {
        "mode": mode,
        "selected": len(selected),
        "queued": queued,
        "alreadyRunning": len(selected) - queued,
        "skipped": with_vocals - len(selected),
        "reasons": reason_counts,
        "results": results,
    }


@celery.task(name="batch_rebuild_artist_credits")
def batch_rebuild_artist_credits(
    mode: str = "preview", run_id: Optional[int] = None
) -> dict:
    """Batch task: re-credit every song and tidy the artist list.

    Looks up every linked recording and its artists on MusicBrainz (cached on
    disk, so the apply after a preview asks nothing again), then makes the
    changes in one transaction. "preview" rolls it back, "apply" commits it;
    both save the same report on the run. See app.services.artist_credits_rebuild.
    """
    from app.config import get_config
    from app.db.database import get_db_session
    from app.services.artist_credits_rebuild import fetch_musicbrainz, rebuild

    cache_dir = get_config().LIBRARY_DIR / "cache" / "musicbrainz"

    with tracked_run(run_id) as run:
        with get_db_session() as session:
            mb = fetch_musicbrainz(
                session, cache_dir, on_total=run.start, on_step=run.song_done
            )
        logger.info(
            "batch_rebuild_artist_credits: %d recordings, %d artists looked up",
            len(mb.recordings),
            len(mb.artists),
        )

        with get_db_session() as session:
            try:
                report = rebuild(session, mb)
            except Exception:
                session.rollback()
                raise
            report["mode"] = mode
            if mode == "apply":
                session.commit()
            else:
                session.rollback()
        run.report(report)

    summary = {
        "mode": mode,
        "songs_changed": report["songs"]["counts"].get("changed", 0),
        "merges": len(report["merges"]),
        "renames": len(report["renames"]),
        "deleted": report["deleted"]["count"],
    }
    logger.info("batch_rebuild_artist_credits: done — %s", summary)
    return summary
