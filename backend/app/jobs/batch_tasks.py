"""Batch Celery tasks for library-wide backfills and alignment.

Each task takes the mode it runs in and the id of the batch_runs row the API
created for it, and reports its progress there after every song. Which songs a
mode selects is defined once, in app.services.batch_jobs.
"""

from typing import Optional

from celery.utils.log import get_task_logger

from ._batch_runs import tracked_run
from .celery_app import celery

logger = get_task_logger(__name__)

# Spacing between iTunes requests, to stay inside its rate limit.
ITUNES_REQUEST_GAP_SECONDS = 1.5


def _select(kind: str, mode: str) -> list:
    from app.db.database import get_db_session
    from app.services.batch_jobs import select_ids

    with get_db_session() as session:
        return select_ids(session, kind, mode)


@celery.task(name="batch_fingerprint_songs")
def batch_fingerprint_songs(
    mode: str = "missing", run_id: Optional[int] = None
) -> dict:
    """Batch task: fingerprint songs via AcoustID."""
    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.acoustid_service import AcoustIdService

    config = get_config()
    counts = {"ok": 0, "no_audio": 0, "error": 0}

    with tracked_run(run_id) as run:
        song_ids = _select("fingerprint", mode)
        run.start(len(song_ids))
        logger.info(
            "batch_fingerprint_songs: processing %d songs (mode=%s)",
            len(song_ids),
            mode,
        )

        for song_id in song_ids:
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
                    AcoustIdService(SongRepository(session)).fingerprint_and_identify(
                        song_id, audio_path
                    )
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


@celery.task(name="batch_backfill_artwork")
def batch_backfill_artwork(mode: str = "missing", run_id: Optional[int] = None) -> dict:
    """Batch task: find each album-less song's album (and its cover) on iTunes.

    "all" looks every song up again.
    """
    import time

    from app.db.database import get_db_session
    from app.db.models.song import DbSong
    from app.services.itunes_service import fetch_and_assign_album_art

    success = 0
    skipped = 0
    errors = 0

    with tracked_run(run_id) as run:
        song_ids = _select("song_albums", mode)
        with get_db_session() as session:
            rows = (
                (
                    session.query(DbSong.id, DbSong.title, DbSong.artist)
                    .filter(DbSong.id.in_(song_ids))
                    .all()
                )
                if song_ids
                else []
            )
        songs = [(row[0], row[1], row[2]) for row in rows]
        run.start(len(songs))
        logger.info(
            "batch_backfill_artwork: processing %d songs (mode=%s)", len(songs), mode
        )

        for i, (song_id, title, artist) in enumerate(songs):
            if not title or not artist:
                skipped += 1
                run.song_done()
                continue
            if i > 0:
                time.sleep(ITUNES_REQUEST_GAP_SECONDS)
            try:
                if fetch_and_assign_album_art(song_id, title, artist):
                    success += 1
                else:
                    skipped += 1
                run.song_done()
            except Exception:
                logger.warning(
                    "batch_backfill_artwork: error for song %s", song_id, exc_info=True
                )
                errors += 1
                run.song_done(ok=False)

    logger.info(
        "batch_backfill_artwork: done — %d succeeded, %d skipped, %d errors",
        success,
        skipped,
        errors,
    )
    return {
        "processed": success + skipped + errors,
        "success": success,
        "skipped": skipped + errors,
    }


@celery.task(name="batch_fetch_album_covers")
def batch_fetch_album_covers(
    mode: str = "missing", run_id: Optional[int] = None
) -> dict:
    """Batch task: download the cover of every album not checked yet."""
    import time

    from app.services.itunes_service import fetch_album_cover

    counts = {"found": 0, "not_found": 0, "error": 0}

    with tracked_run(run_id) as run:
        album_ids = _select("album_covers", mode)
        run.start(len(album_ids))
        logger.info("batch_fetch_album_covers: processing %d albums", len(album_ids))

        for i, album_id in enumerate(album_ids):
            if i > 0:
                time.sleep(ITUNES_REQUEST_GAP_SECONDS)
            try:
                outcome = fetch_album_cover(album_id)
            except Exception:
                logger.warning(
                    "batch_fetch_album_covers: error for album %s",
                    album_id,
                    exc_info=True,
                )
                outcome = "error"
            counts[outcome] += 1
            run.song_done(ok=outcome != "error")

    logger.info("batch_fetch_album_covers: done — %s", counts)
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
        song_ids = _select("duration", mode)
        run.start(len(song_ids))
        logger.info(
            "batch_backfill_duration: processing %d songs (mode=%s)",
            len(song_ids),
            mode,
        )

        for song_id in song_ids:
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
        song_ids = _select("vocal_range", mode)
        run.start(len(song_ids))
        logger.info(
            "batch_backfill_vocal_range: processing %d songs (mode=%s)",
            len(song_ids),
            mode,
        )

        for i, song_id in enumerate(song_ids, 1):
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
        song_ids = _select("loudness", mode)
        run.start(len(song_ids))
        logger.info(
            "batch_backfill_loudness: processing %d songs (mode=%s)",
            len(song_ids),
            mode,
        )

        for i, song_id in enumerate(song_ids, 1):
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


@celery.task(name="batch_fetch_artist_images")
def batch_fetch_artist_images(
    mode: str = "missing", run_id: Optional[int] = None
) -> dict:
    """Batch task: fetch a Discogs image for every artist not checked yet.

    One artist at a time, to stay inside Discogs' rate limit.
    """
    import asyncio

    from app.db.database import SessionLocal, get_db_session
    from app.db.models import DbArtist
    from app.services.artist_image_service import ArtistImageService
    from app.services.file_service import FileService

    counts = {"fetched": 0, "not_found": 0, "errors": 0}

    with tracked_run(run_id) as run:
        artist_ids = _select("artist_images", mode)
        with get_db_session() as session:
            names = (
                [
                    row[0]
                    for row in session.query(DbArtist.name)
                    .filter(DbArtist.id.in_(artist_ids))
                    .all()
                ]
                if artist_ids
                else []
            )
        run.start(len(names))
        logger.info("batch_fetch_artist_images: processing %d artists", len(names))

        service = ArtistImageService(FileService(), SessionLocal)
        for name in names:
            try:
                path = asyncio.run(service.get_or_fetch_artist_image(name))
                counts["fetched" if path is not None else "not_found"] += 1
                run.song_done()
            except Exception:
                logger.warning(
                    "batch_fetch_artist_images: error for artist %s",
                    name,
                    exc_info=True,
                )
                counts["errors"] += 1
                run.song_done(ok=False)

    logger.info("batch_fetch_artist_images: done — %s", counts)
    return counts


@celery.task(name="batch_align_lyrics")
def batch_align_lyrics(mode: str = "missing", run_id: Optional[int] = None) -> dict:
    """Batch task: queue align_song_lyrics for every song a `mode` run selects.

    Each song runs as its own job on the lyrics queue, exactly like a new
    song's alignment: in its own language, with remote candidates, the offset
    sweep and ASR re-timing, and respecting hand-picked and rejected lyrics.
    The run row records how many were queued; alignment progress after that
    shows in the alignment counts as each song finishes.
    """
    from app.db.database import get_db_session
    from app.jobs.lyrics_dispatch import enqueue_song_alignment
    from app.services.lyrics_repair import count_reasons, select_songs_for_alignment

    selected: list = []
    with_vocals = 0
    reason_counts: dict = {}
    results: list = []
    queued = 0

    with tracked_run(run_id) as run:
        with get_db_session() as session:
            selected, with_vocals = select_songs_for_alignment(session, mode)
            reason_counts = count_reasons(selected)
            run.start(len(selected))
            for song, reasons in selected:
                dispatch = enqueue_song_alignment(song, include_remote=True)
                queued += int(dispatch["dispatched"])
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
