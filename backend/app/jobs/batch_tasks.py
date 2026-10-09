"""Batch Celery tasks for library-wide backfills and alignment."""

from celery.utils.log import get_task_logger

from .celery_app import celery

logger = get_task_logger(__name__)


@celery.task(name="batch_fingerprint_songs")
def batch_fingerprint_songs(reprocess_all: bool = False) -> None:
    """Batch task: fingerprint songs via AcoustID."""
    from app.config import get_config
    from app.db.database import get_db_session
    from app.db.models.song import DbSong
    from app.repositories.song_repository import SongRepository
    from app.services.acoustid_service import AcoustIdService

    config = get_config()

    with get_db_session() as session:
        query = session.query(DbSong.id)
        if not reprocess_all:
            query = query.filter(DbSong.acoustid_fingerprint_status == "not_checked")
        song_ids = [row[0] for row in query.all()]

    logger.info("batch_fingerprint_songs: processing %d songs", len(song_ids))

    for song_id in song_ids:
        song_dir = config.BASE_LIBRARY_DIR / song_id
        original_path = song_dir / "original.mp3"
        instrumental_path = song_dir / "instrumental.mp3"
        vocals_path = song_dir / "vocals.mp3"
        audio_path = (
            original_path if original_path.exists()
            else instrumental_path if instrumental_path.exists()
            else vocals_path
        )

        if not audio_path.exists():
            logger.warning("batch_fingerprint_songs: no audio for song %s, skipping", song_id)
            with get_db_session() as session:
                SongRepository(session).update(song_id, acoustid_fingerprint_status="failed")
            continue

        try:
            with get_db_session() as session:
                AcoustIdService(SongRepository(session)).fingerprint_and_identify(song_id, audio_path)
        except Exception:
            logger.warning("batch_fingerprint_songs: error processing song %s", song_id, exc_info=True)

    logger.info("batch_fingerprint_songs: done")


@celery.task(name="batch_backfill_artwork")
def batch_backfill_artwork(force: bool = False) -> dict:
    """Batch task: backfill album art for songs missing it."""
    from app.db.database import get_db_session
    from app.db.models.song import DbSong
    from app.services.itunes_service import fetch_and_assign_album_art

    with get_db_session() as session:
        query = session.query(DbSong.id, DbSong.title, DbSong.artist)
        if not force:
            query = query.filter(DbSong.album_id.is_(None))
        rows = query.all()

    song_ids = [(row[0], row[1], row[2]) for row in rows]
    logger.info("batch_backfill_artwork: processing %d songs", len(song_ids))

    success = 0
    skipped = 0
    for i, (song_id, title, artist) in enumerate(song_ids):
        if not title or not artist:
            skipped += 1
            continue
        if i > 0:
            import time

            time.sleep(1.5)
        try:
            got = fetch_and_assign_album_art(song_id, title, artist)
            if got:
                success += 1
            else:
                skipped += 1
        except Exception:
            logger.warning("batch_backfill_artwork: error for song %s", song_id, exc_info=True)
            skipped += 1

    logger.info("batch_backfill_artwork: done — %d succeeded, %d skipped", success, skipped)
    return {"processed": len(song_ids), "success": success, "skipped": skipped}


@celery.task(name="batch_backfill_duration")
def batch_backfill_duration(mode: str = "missing") -> dict:
    """Batch task: populate duration from original audio file."""
    from pathlib import Path

    import librosa

    from app.config import get_config
    from app.db.database import get_db_session
    from app.db.models.song import DbSong
    from app.repositories.song_repository import SongRepository

    config = get_config()

    with get_db_session() as session:
        query = session.query(DbSong.id)
        if mode == "missing":
            query = query.filter(DbSong.duration.is_(None))
        rows = query.all()

    song_ids = [row[0] for row in rows]
    logger.info("batch_backfill_duration: processing %d songs (mode=%s)", len(song_ids), mode)

    success = 0
    skipped = 0
    for song_id in song_ids:
        audio_path = Path(config.BASE_LIBRARY_DIR) / song_id / "original.mp3"
        if not audio_path.exists():
            skipped += 1
            continue
        try:
            duration = librosa.get_duration(path=str(audio_path))
            with get_db_session() as session:
                SongRepository(session).update(song_id, duration=duration)
            success += 1
        except Exception:
            logger.warning("batch_backfill_duration: error for song %s", song_id, exc_info=True)
            skipped += 1

    logger.info("batch_backfill_duration: done — %d updated, %d skipped", success, skipped)
    return {"processed": len(song_ids), "success": success, "skipped": skipped}


@celery.task(name="batch_backfill_vocal_range")
def batch_backfill_vocal_range(mode: str = "missing") -> dict:
    """Batch task: detect vocal range from each song's vocals stem.

    Runs songs one after another inside this single task (~10-30s each) rather
    than fanning out per-song tasks, so a long backfill occupies one enrichment
    slot and new downloads can still post-process alongside it. Each song is
    saved as it finishes, so re-running with mode="missing" resumes.
    """
    from app.db.database import get_db_session
    from app.db.models.song import DbSong

    from .metadata_tasks import detect_and_store_vocal_range

    with get_db_session() as session:
        query = session.query(DbSong.id)
        if mode == "missing":
            query = query.filter(DbSong.vocal_range_low.is_(None))
        song_ids = [row[0] for row in query.all()]

    logger.info("batch_backfill_vocal_range: processing %d songs (mode=%s)", len(song_ids), mode)

    counts = {"ok": 0, "no_range": 0, "no_audio": 0, "error": 0}
    for i, song_id in enumerate(song_ids, 1):
        counts[detect_and_store_vocal_range(song_id)] += 1
        if i % 25 == 0:
            logger.info("batch_backfill_vocal_range: %d/%d done %s", i, len(song_ids), counts)

    logger.info("batch_backfill_vocal_range: done — %s", counts)
    return {
        "processed": len(song_ids),
        "success": counts["ok"],
        "skipped": counts["no_range"] + counts["no_audio"] + counts["error"],
        **counts,
    }


@celery.task(name="batch_backfill_loudness")
def batch_backfill_loudness(mode: str = "missing") -> dict:
    """Batch task: measure each song's loudness from its stems and store its gain.

    Runs songs one after another inside this single task (a second or two each)
    rather than fanning out per-song tasks, so new downloads can still
    post-process alongside it. Each song is saved as it finishes, so re-running
    with mode="missing" resumes.
    """
    from app.db.database import get_db_session
    from app.db.models.song import DbSong

    from .metadata_tasks import detect_and_store_loudness

    with get_db_session() as session:
        query = session.query(DbSong.id)
        if mode == "missing":
            query = query.filter(DbSong.loudness_lufs.is_(None))
        song_ids = [row[0] for row in query.all()]

    logger.info(
        "batch_backfill_loudness: processing %d songs (mode=%s)", len(song_ids), mode
    )

    counts = {"ok": 0, "silent": 0, "no_audio": 0, "error": 0}
    for i, song_id in enumerate(song_ids, 1):
        counts[detect_and_store_loudness(song_id)] += 1
        if i % 25 == 0:
            logger.info(
                "batch_backfill_loudness: %d/%d done %s", i, len(song_ids), counts
            )

    logger.info("batch_backfill_loudness: done — %s", counts)
    return {
        "processed": len(song_ids),
        "success": counts["ok"],
        "skipped": counts["silent"] + counts["no_audio"] + counts["error"],
        **counts,
    }


@celery.task(name="batch_align_lyrics")
def batch_align_lyrics(mode: str = "missing") -> dict:
    """Batch task: queue align_song_lyrics for every song a `mode` run selects.

    Each song runs as its own job on the lyrics queue, exactly like a new
    song's alignment: in its own language, with remote candidates, the offset
    sweep and ASR re-timing, and respecting hand-picked and rejected lyrics.
    """
    from app.db.database import get_db_session
    from app.jobs.lyrics_dispatch import enqueue_song_alignment
    from app.services.lyrics_repair import count_reasons, select_songs_for_alignment

    with get_db_session() as session:
        selected, with_vocals = select_songs_for_alignment(session, mode)
        reason_counts = count_reasons(selected)
        results = []
        queued = 0
        for song, reasons in selected:
            dispatch = enqueue_song_alignment(song, include_remote=True)
            queued += int(dispatch["dispatched"])
            results.append({
                "songId": song.id,
                "title": f"{song.artist or '?'} — {song.title or song.id}",
                "status": "queued" if dispatch["dispatched"] else "already_running",
                "reasons": reasons,
            })

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
