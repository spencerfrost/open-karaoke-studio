"""Enrichment and maintenance Celery tasks."""

from pathlib import Path

from app.services.audio import detect_loudness, detect_vocal_range
from app.services.chord_detection_service import detect_chords
from celery.utils.log import get_task_logger

from .celery_app import celery

logger = get_task_logger(__name__)


@celery.task(bind=True, name="cleanup_old_jobs")
def cleanup_old_jobs(self):
    """Periodically clean up old job records and temporary files."""
    logger.debug("Running job cleanup task")
    # Implement cleanup logic here


def _run_post_processing(song_id: str, song_dir: Path) -> None:
    """Run all enrichment steps after audio separation. Failures are logged only."""
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    vocals_path = song_dir / "vocals.mp3"
    instrumental_path = song_dir / "instrumental.mp3"
    update_kwargs = {}

    try:
        if vocals_path.exists():
            vocal_range = detect_vocal_range(vocals_path, lambda msg: logger.debug("VocalRange: %s", msg))
            if vocal_range:
                update_kwargs["vocal_range_low"] = vocal_range[0]
                update_kwargs["vocal_range_high"] = vocal_range[1]
    except Exception as e:
        logger.warning("Vocal range detection failed for song %s: %s", song_id, e)

    try:
        if instrumental_path.exists():
            chord_data = detect_chords(str(instrumental_path))
            if chord_data:
                update_kwargs["chords_data"] = chord_data
    except Exception as e:
        logger.warning("Chord detection failed for song %s: %s", song_id, e)

    try:
        if instrumental_path.exists():
            loudness_result = detect_loudness(instrumental_path, lambda msg: logger.debug("Loudness: %s", msg))
            if loudness_result:
                update_kwargs["loudness_dbfs"] = loudness_result[0]
                update_kwargs["gain_db"] = loudness_result[1]
    except Exception as e:
        logger.warning("Loudness detection failed for song %s: %s", song_id, e)

    try:
        with get_db_session() as session:
            repo = SongRepository(session)
            song = repo.fetch(song_id)
            song_title = song.title if song else None
            song_artist = song.artist if song else None
            video_id = song.video_id if song else None

        album_art_assigned = False
        if song_title and song_artist:
            from app.services.itunes_service import fetch_and_assign_album_art

            album_art_assigned = fetch_and_assign_album_art(song_id, song_title, song_artist)
            if album_art_assigned:
                logger.info("Album art downloaded for song %s", song_id)

        if not album_art_assigned and video_id:
            from app.services.youtube_service import YouTubeService

            youtube_service = YouTubeService()
            youtube_service.fetch_and_save_thumbnail(video_id, song_id)
            logger.info("Thumbnail downloaded for song %s (iTunes had no match)", song_id)
    except Exception as e:
        logger.warning("Artwork fetch failed for song %s: %s", song_id, e)

    if update_kwargs:
        with get_db_session() as session:
            repo = SongRepository(session)
            repo.update(song_id, **update_kwargs)
        logger.info("Post-processing complete for song %s (%s fields updated)", song_id, len(update_kwargs))

    try:
        original_path = song_dir / "original.mp3"
        audio_path = original_path if original_path.exists() else instrumental_path if instrumental_path.exists() else vocals_path
        if audio_path.exists():
            from app.services.acoustid_service import AcoustIdService

            with get_db_session() as session:
                repo = SongRepository(session)
                AcoustIdService(repo).fingerprint_and_identify(song_id, audio_path)
        else:
            logger.warning("AcoustID: no audio file found for song %s", song_id)
    except Exception:
        logger.warning("AcoustID fingerprinting failed for song %s", song_id, exc_info=True)

    try:
        from app.services.song_artist_service import populate_song_artists

        with get_db_session() as session:
            repo = SongRepository(session)
            song = repo.fetch(song_id)
            if song and song.artist:
                populate_song_artists(session, song, song.artist)
    except Exception:
        logger.warning("song_artists population failed for song %s", song_id, exc_info=True)


@celery.task(bind=True, name="post_process_song")
def post_process_song(self, song_id: str) -> None:
    """
    DEPRECATED: Serial enrichment task used by upload flow.

    process_youtube_job dispatches per-step enrichment tasks as soon as each input is available.
    """
    logger.info("Starting post-processing for song %s", song_id)

    from app.config import get_config

    config = get_config()
    song_dir = Path(config.BASE_LIBRARY_DIR) / song_id

    if not song_dir.exists():
        logger.error("post_process_song: song directory not found for song %s", song_id)
        return

    try:
        _run_post_processing(song_id, song_dir)
    except Exception as e:
        logger.error("post_process_song failed for song %s: %s", song_id, e, exc_info=True)
