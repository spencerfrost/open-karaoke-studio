"""Batch Celery tasks for library-wide backfills and alignment."""

from app.services.lyrics_selection import SongData
from celery.utils.log import get_task_logger

from .celery_app import celery
from .lyrics_support import build_alignment_attempts_for_song

logger = get_task_logger(__name__)


def _build_alignment_attempts(song: SongData, include_remote: bool = True, max_remote_results: int = 3) -> list[dict]:
    return build_alignment_attempts_for_song(
        song,
        include_remote=include_remote,
        max_remote_results=max_remote_results,
    )


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


@celery.task(name="batch_align_lyrics")
def batch_align_lyrics(mode: str = "missing", language: str = "en") -> dict:
    """Batch task: run WhisperX forced alignment across the library."""
    import json as _json

    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.file_service import FileService
    from app.services.lyrics_alignment import (
        align_lyrics_to_vocals_with_model,
        align_plain_lyrics_to_vocals_with_model,
        load_alignment_model,
    )

    MIN_SCORE = 0.5
    file_service = FileService()

    with get_db_session() as session:
        all_songs = SongRepository(session).fetch_all()
        song_ids = [s.id for s in all_songs]

    logger.info("batch_align_lyrics: found %d songs (mode=%s)", len(song_ids), mode)

    eligible = []
    for song_id in song_ids:
        vocals_path = file_service.get_vocals_path(song_id, ".mp3")
        if not vocals_path.exists():
            continue
        with get_db_session() as session:
            song = SongRepository(session).fetch(song_id)
            if not song:
                continue
            if mode == "missing" and song.word_synced_lyrics:
                continue
            if not song.synced_lyrics and not song.plain_lyrics:
                continue
        eligible.append(song_id)

    total_songs = len(song_ids)
    if not eligible:
        logger.info("batch_align_lyrics: no eligible songs — done")
        return {
            "processed": 0,
            "activated": 0,
            "failed": 0,
            "skipped": total_songs,
            "results": [],
        }

    logger.info("batch_align_lyrics: loading wav2vec2 model for %d songs", len(eligible))
    model_a, metadata = load_alignment_model(language=language)

    MIN_SCORE = 0.3
    results = []
    activated = 0
    failed = 0

    for song_id in eligible:
        vocals_path = file_service.get_vocals_path(song_id, ".mp3")
        with get_db_session() as session:
            song = SongRepository(session).fetch(song_id)
            if not song:
                failed += 1
                results.append({"songId": song_id, "status": "failed", "reason": "song not found"})
                continue
            song_label = f"{song.artist or '?'} — {song.title or song_id}"
            song_data: SongData = {
                "id": song.id,
                "title": song.title,
                "artist": song.artist,
                "album": song.album,
                "plain_lyrics": song.plain_lyrics,
                "synced_lyrics": song.synced_lyrics,
                "word_synced_lyrics": song.word_synced_lyrics,
            }

        attempts = _build_alignment_attempts(song_data, include_remote=False)
        if not attempts:
            failed += 1
            results.append({"songId": song_id, "title": song_label, "status": "failed", "reason": "no source lyrics"})
            continue
        best_result = None
        best_attempt = None
        align_error_count = 0

        for idx, attempt in enumerate(attempts):
            source_content = attempt["content"]
            use_plain = attempt["source_type"] == "plain"

            try:
                result = (
                    align_plain_lyrics_to_vocals_with_model(source_content, vocals_path, model_a, metadata, language=language)
                    if use_plain
                    else align_lyrics_to_vocals_with_model(source_content, vocals_path, model_a, metadata, language=language)
                )
            except Exception as e:
                align_error_count += 1
                logger.warning(
                    "batch_align_lyrics: attempt failed for %s (source=%s): %s",
                    song_label,
                    attempt["source"],
                    e,
                    exc_info=True,
                )
                continue

            if not result:
                continue

            if not best_result or result["mean_score"] > best_result["mean_score"]:
                best_result = result
                best_attempt = attempt

            if result["mean_score"] >= MIN_SCORE:
                with get_db_session() as session:
                    song = SongRepository(session).fetch(song_id)
                    song.word_synced_lyrics = _json.dumps({
                        "words": result["words"],
                        "instrumental_intervals": result.get("instrumental_intervals", []),
                        "language": result["language"],
                        "mean_score": result["mean_score"],
                        "word_count": result["word_count"],
                        "line_count": result["line_count"],
                        "aligned_at": result["aligned_at"],
                        "lyrics_source_type": attempt["source_type"],
                        "lyrics_source": attempt["source"],
                        "lyrics_attempt": idx + 1,
                    })
                    if attempt["persist"]:
                        if attempt["source_type"] == "plain" and not song.plain_lyrics:
                            song.plain_lyrics = attempt["content"]
                        if attempt["source_type"] == "synced" and not song.synced_lyrics:
                            song.synced_lyrics = attempt["content"]
                    session.commit()
                activated += 1
                results.append({
                    "songId": song_id,
                    "title": song_label,
                    "status": "activated",
                    "meanScore": result["mean_score"],
                    "wordCount": result["word_count"],
                    "sourceType": attempt["source_type"],
                    "source": attempt["source"],
                })
                logger.info(
                    "batch_align_lyrics %s: activated (score=%.3f, source=%s)",
                    song_label,
                    result["mean_score"],
                    attempt["source"],
                )
                break
        else:
            failed += 1
            if best_result and best_attempt:
                results.append({
                    "songId": song_id,
                    "title": song_label,
                    "status": "low_confidence",
                    "meanScore": best_result["mean_score"],
                    "wordCount": best_result["word_count"],
                    "sourceType": best_attempt["source_type"],
                    "source": best_attempt["source"],
                    "attempted": len(attempts),
                    "errors": align_error_count,
                })
                logger.info(
                    "batch_align_lyrics %s: low_confidence (score=%.3f, source=%s)",
                    song_label,
                    best_result["mean_score"],
                    best_attempt["source"],
                )
            else:
                results.append({
                    "songId": song_id,
                    "title": song_label,
                    "status": "failed",
                    "reason": "alignment produced no words",
                    "attempted": len(attempts),
                    "errors": align_error_count,
                })
                logger.info("batch_align_lyrics %s: failed after %d attempts", song_label, len(attempts))

    logger.info("batch_align_lyrics: done — activated=%d, failed=%d", activated, failed)
    return {
        "processed": len(eligible),
        "activated": activated,
        "failed": failed,
        "skipped": total_songs - len(eligible),
        "results": results,
    }
