"""Metadata and enrichment Celery tasks."""

from pathlib import Path

from celery.utils.log import get_task_logger

from app.services.audio import detect_loudness, detect_vocal_range

from .celery_app import celery

logger = get_task_logger(__name__)


@celery.task(name="fetch_song_artwork")
def fetch_song_artwork(song_id: str) -> dict:
    """Find the song's album and cover, falling back to its YouTube thumbnail."""
    logger.info("[PIPELINE] fetch_song_artwork starting for song %s", song_id)
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.album_service import refresh_song_album

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if not song:
            logger.warning("fetch_song_artwork: song %s not found", song_id)
            return {"status": "not_found", "song_id": song_id}
        video_id = song.video_id

    try:
        outcome = refresh_song_album(song_id)
    except Exception:
        logger.warning(
            "fetch_song_artwork: album lookup failed for song %s",
            song_id,
            exc_info=True,
        )
        outcome = "error"

    if outcome != "found" and video_id:
        try:
            from app.services.youtube_service import YouTubeService

            YouTubeService().fetch_and_save_thumbnail(video_id, song_id)
            logger.info(
                "fetch_song_artwork: YouTube thumbnail saved for song %s", song_id
            )
        except Exception:
            logger.warning(
                "fetch_song_artwork: thumbnail download failed for song %s",
                song_id,
                exc_info=True,
            )

    return {"status": "ok", "album": outcome, "song_id": song_id}


def detect_and_store_loudness(song_id: str) -> str:
    """Measure how loud a song plays by default and save its normalization gain.

    Returns "ok", "silent", "no_audio" (no instrumental stem yet), or "error".
    Shared by the per-song pipeline task and the library-wide backfill.
    """
    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    song_dir = Path(get_config().BASE_LIBRARY_DIR) / song_id
    try:
        result = detect_loudness(song_dir)
    except FileNotFoundError:
        logger.warning(
            "detect_loudness: instrumental.mp3 not found for song %s", song_id
        )
        return "no_audio"
    except Exception:
        logger.warning("detect_loudness: failed for song %s", song_id, exc_info=True)
        return "error"

    if result is None:
        logger.warning(
            "detect_loudness: song %s is silent, leaving its gain unset", song_id
        )
        return "silent"

    with get_db_session() as session:
        SongRepository(session).update(
            song_id,
            loudness_lufs=result.loudness_lufs,
            true_peak_dbtp=result.true_peak_dbtp,
            gain_db=result.gain_db,
        )
    return "ok"


@celery.task(name="detect_song_loudness")
def detect_song_loudness(song_id: str) -> dict:
    """Measure the separated stems' loudness and store the gain the player applies."""
    logger.info("[PIPELINE] detect_song_loudness starting for song %s", song_id)
    return {"status": detect_and_store_loudness(song_id), "song_id": song_id}


def detect_and_store_singing_map(song_id: str) -> str:
    """Measure when the lead and backing vocals are singing and save the map.

    Returns "ok", "no_audio" (no lead vocal stem yet) or "error". Shared by the
    per-song pipeline task, the library-wide backfill and the admin review
    page (which measures a song on request).
    """
    import json

    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.singing_map import measure_singing_map

    song_dir = Path(get_config().BASE_LIBRARY_DIR) / song_id
    try:
        singing_map = measure_singing_map(song_dir)
    except FileNotFoundError:
        logger.warning("singing map: vocals.mp3 not found for song %s", song_id)
        return "no_audio"
    except Exception:
        logger.warning("singing map: failed for song %s", song_id, exc_info=True)
        return "error"

    with get_db_session() as session:
        SongRepository(session).update(song_id, singing_map=json.dumps(singing_map))
    return "ok"


@celery.task(name="detect_song_singing_map")
def detect_song_singing_map(song_id: str) -> dict:
    """Measure when the separated lead and backing vocals are singing."""
    logger.info("[PIPELINE] detect_song_singing_map starting for song %s", song_id)
    return {"status": detect_and_store_singing_map(song_id), "song_id": song_id}


def detect_and_store_vocal_range(song_id: str) -> str:
    """Detect a song's vocal range from vocals.mp3 and save it.

    Returns "ok", "no_range" (too few voiced frames), "no_audio", or "error".
    Shared by the per-song pipeline task and the library-wide backfill.
    """
    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    vocals_path = Path(get_config().BASE_LIBRARY_DIR) / song_id / "vocals.mp3"
    if not vocals_path.exists():
        logger.warning("detect_vocal_range: vocals.mp3 not found for song %s", song_id)
        return "no_audio"

    try:
        result = detect_vocal_range(
            vocals_path, lambda msg: logger.debug("VocalRange: %s", msg)
        )
    except Exception:
        logger.warning("detect_vocal_range: failed for song %s", song_id, exc_info=True)
        return "error"

    if not result:
        return "no_range"

    with get_db_session() as session:
        SongRepository(session).update(
            song_id, vocal_range_low=result[0], vocal_range_high=result[1]
        )
    logger.info("detect_vocal_range: %s-%s for song %s", result[0], result[1], song_id)
    return "ok"


@celery.task(name="detect_song_vocal_range")
def detect_song_vocal_range(song_id: str) -> dict:
    """Detect vocal pitch range from vocals.mp3 and store note names."""
    logger.info("[PIPELINE] detect_song_vocal_range starting for song %s", song_id)
    return {"status": detect_and_store_vocal_range(song_id), "song_id": song_id}


@celery.task(name="fingerprint_single_song")
def fingerprint_single_song(song_id: str) -> dict:
    """Fingerprint a single song via AcoustID."""
    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.acoustid_service import AcoustIdService

    config = get_config()
    song_dir = Path(config.BASE_LIBRARY_DIR) / song_id
    original = song_dir / "original.mp3"
    instrumental = song_dir / "instrumental.mp3"
    vocals = song_dir / "vocals.mp3"
    audio_path = (
        original
        if original.exists()
        else (
            instrumental
            if instrumental.exists()
            else vocals if vocals.exists() else None
        )
    )

    with get_db_session() as session:
        if audio_path is None:
            logger.warning(
                "fingerprint_single_song: no audio file found for song %s", song_id
            )
            SongRepository(session).update(
                song_id, acoustid_fingerprint_status="failed"
            )
            return {"status": "no_audio", "song_id": song_id}
        try:
            outcome = AcoustIdService(SongRepository(session)).fingerprint_and_link(
                song_id, audio_path
            )
        except Exception:
            logger.exception("fingerprint_single_song: failed for song %s", song_id)
            return {"status": "error", "song_id": song_id}

    # Credits follow the linked recording; a suggestion links none.
    if outcome == "matched":
        logger.debug(
            "[PIPELINE] fingerprint linked - dispatching enrich_song_artist_credits for song %s",
            song_id,
        )
        celery.send_task("enrich_song_artist_credits", args=[song_id])

    return {"status": outcome, "song_id": song_id}


@celery.task(name="enrich_song_artist_credits")
def enrich_song_artist_credits(song_id: str, picked: bool = False) -> dict:
    """Credit a song from its MusicBrainz recording, and set its show name.

    A confirmed song keeps its credits unless `picked`: a person choosing the
    recording just now, which is when its credits should be used. With no
    recording credits the song keeps the ones it has. Never touches the
    artist text. The show follows the recording unless a person set it.
    """
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.musicbrainz_service import get_recording_details
    from app.services.show_name_service import store_detected_show
    from app.services.song_artist_service import set_song_credits

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if not song:
            logger.warning("enrich_song_artist_credits: song %s not found", song_id)
            return {"status": "not_found", "song_id": song_id}
        if not song.musicbrainz_recording_id:
            # The recording it was linked to may have been taken away
            store_detected_show(song, None)
            session.commit()
            return {"status": "no_recording", "song_id": song_id}

        # One recording lookup feeds both the show name and the artist credits.
        try:
            details = get_recording_details(song.musicbrainz_recording_id)
        except Exception:
            logger.warning(
                "MusicBrainz recording lookup failed for song %s",
                song_id,
                exc_info=True,
            )
            return {"status": "error", "song_id": song_id}
        if details is None:
            logger.warning("MusicBrainz recording lookup failed for song %s", song_id)
            return {"status": "error", "song_id": song_id}
        show_name, recording_credits = details
        store_detected_show(song, show_name)

        if not recording_credits:
            session.commit()
            logger.info("No recording credits for song %s; kept its own", song_id)
            return {"status": "no_credits", "song_id": song_id}

        if song.metadata_confirmed_at and not picked:
            session.commit()
            logger.info("Kept song_artists for confirmed song %s", song_id)
            return {"status": "confirmed", "song_id": song_id}

        set_song_credits(session, song, recording_credits)
        session.commit()

    return {"status": "ok", "song_id": song_id}
