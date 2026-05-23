"""Metadata and enrichment Celery tasks."""

from pathlib import Path

from app.services.audio import detect_loudness, detect_vocal_range
from app.services.chord_detection_service import detect_chords
from celery.utils.log import get_task_logger

from .celery_app import celery

logger = get_task_logger(__name__)


@celery.task(name="fetch_song_artwork")
def fetch_song_artwork(song_id: str) -> dict:
    """Fetch album art via iTunes (falling back to YouTube thumbnail). No audio required."""
    logger.info("[PIPELINE] fetch_song_artwork starting for song %s", song_id)
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.itunes_service import fetch_and_assign_album_art

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if not song:
            logger.warning("fetch_song_artwork: song %s not found", song_id)
            return {"status": "not_found", "song_id": song_id}
        song_title = song.title
        song_artist = song.artist
        video_id = song.video_id

    assigned = False
    if song_title and song_artist:
        try:
            assigned = fetch_and_assign_album_art(song_id, song_title, song_artist)
            if assigned:
                logger.info("fetch_song_artwork: iTunes art assigned for song %s", song_id)
        except Exception:
            logger.warning("fetch_song_artwork: iTunes lookup failed for song %s", song_id, exc_info=True)

    if not assigned and video_id:
        try:
            from app.services.youtube_service import YouTubeService

            YouTubeService().fetch_and_save_thumbnail(video_id, song_id)
            logger.info("fetch_song_artwork: YouTube thumbnail saved for song %s", song_id)
        except Exception:
            logger.warning("fetch_song_artwork: thumbnail download failed for song %s", song_id, exc_info=True)

    return {"status": "ok", "song_id": song_id}


@celery.task(name="detect_song_loudness")
def detect_song_loudness(song_id: str) -> dict:
    """Measure loudness from original.mp3 and store gain correction value."""
    logger.info("[PIPELINE] detect_song_loudness starting for song %s", song_id)
    from app.config import get_config
    from app.db.database import get_db_session

    config = get_config()
    audio_path = Path(config.BASE_LIBRARY_DIR) / song_id / "original.mp3"

    if not audio_path.exists():
        logger.warning("detect_song_loudness: original.mp3 not found for song %s", song_id)
        return {"status": "no_audio", "song_id": song_id}

    try:
        result = detect_loudness(audio_path, lambda msg: logger.debug("Loudness: %s", msg))
    except Exception:
        logger.warning("detect_song_loudness: failed for song %s", song_id, exc_info=True)
        return {"status": "error", "song_id": song_id}

    if result:
        with get_db_session() as session:
            from app.repositories.song_repository import SongRepository as _Repo

            _Repo(session).update(song_id, loudness_dbfs=result[0], gain_db=result[1])
        logger.info("detect_song_loudness: %.2f dBFS (gain %.2f dB) for song %s", result[0], result[1], song_id)

    return {"status": "ok", "song_id": song_id}


@celery.task(name="detect_song_vocal_range")
def detect_song_vocal_range(song_id: str) -> dict:
    """Detect vocal pitch range from vocals.mp3 and store note names."""
    logger.info("[PIPELINE] detect_song_vocal_range starting for song %s", song_id)
    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    config = get_config()
    vocals_path = Path(config.BASE_LIBRARY_DIR) / song_id / "vocals.mp3"

    if not vocals_path.exists():
        logger.warning("detect_song_vocal_range: vocals.mp3 not found for song %s", song_id)
        return {"status": "no_audio", "song_id": song_id}

    try:
        result = detect_vocal_range(vocals_path, lambda msg: logger.debug("VocalRange: %s", msg))
    except Exception:
        logger.warning("detect_song_vocal_range: failed for song %s", song_id, exc_info=True)
        return {"status": "error", "song_id": song_id}

    if result:
        with get_db_session() as session:
            SongRepository(session).update(song_id, vocal_range_low=result[0], vocal_range_high=result[1])
        logger.info("detect_song_vocal_range: %s-%s for song %s", result[0], result[1], song_id)

    return {"status": "ok", "song_id": song_id}


@celery.task(name="detect_song_chords")
def detect_song_chords(song_id: str) -> dict:
    """Detect chord progression from instrumental.mp3 and store beat-synced chord list."""
    logger.info("[PIPELINE] detect_song_chords starting for song %s", song_id)
    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    config = get_config()
    instrumental_path = Path(config.BASE_LIBRARY_DIR) / song_id / "instrumental.mp3"

    if not instrumental_path.exists():
        logger.warning("detect_song_chords: instrumental.mp3 not found for song %s", song_id)
        return {"status": "no_audio", "song_id": song_id}

    try:
        chord_data = detect_chords(str(instrumental_path))
    except Exception:
        logger.warning("detect_song_chords: failed for song %s", song_id, exc_info=True)
        return {"status": "error", "song_id": song_id}

    if chord_data:
        with get_db_session() as session:
            SongRepository(session).update(song_id, chords_data=chord_data)
        logger.info("detect_song_chords: %d chords stored for song %s", len(chord_data), song_id)

    return {"status": "ok", "song_id": song_id}


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
        original if original.exists()
        else instrumental if instrumental.exists()
        else vocals if vocals.exists()
        else None
    )

    with get_db_session() as session:
        if audio_path is None:
            logger.warning("fingerprint_single_song: no audio file found for song %s", song_id)
            SongRepository(session).update(song_id, acoustid_fingerprint_status="failed")
            return {"status": "no_audio", "song_id": song_id}
        try:
            AcoustIdService(SongRepository(session)).fingerprint_and_identify(song_id, audio_path)
        except Exception:
            logger.exception("fingerprint_single_song: failed for song %s", song_id)

    logger.debug("[PIPELINE] fingerprint complete - dispatching enrich_song_artist_credits for song %s", song_id)
    celery.send_task("enrich_song_artist_credits", args=[song_id])

    return {"status": "ok", "song_id": song_id}


@celery.task(name="enrich_song_artist_credits")
def enrich_song_artist_credits(song_id: str) -> dict:
    """Re-resolve artist credits for a single song using MB recording -> MB search -> regex."""
    from app.db.database import get_db_session
    from app.db.models.song_artist import DbSongArtist
    from app.repositories.artist_repository import ArtistRepository
    from app.repositories.song_repository import SongRepository
    from app.services.credits_resolver import resolve_artist_credits
    from app.services.song_artist_service import try_ampersand_split

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if not song:
            logger.warning("enrich_song_artist_credits: song %s not found", song_id)
            return {"status": "not_found", "song_id": song_id}

        credits = resolve_artist_credits(
            title=song.title,
            artist_str=song.artist,
            recording_id=song.musicbrainz_recording_id,
        )

        credits = try_ampersand_split(credits, session)

        artist_repo = ArtistRepository(session)

        session.query(DbSongArtist).filter(DbSongArtist.song_id == song.id).delete()

        first_primary_set = False
        for i, (name, role) in enumerate(credits):
            artist = artist_repo.get_or_create(name, display_name=name)
            if not first_primary_set and role == "primary":
                song.artist_id = artist.id
                first_primary_set = True
            session.add(
                DbSongArtist(
                    song_id=song.id,
                    artist_id=artist.id,
                    role=role,
                    display_order=i,
                )
            )

        session.commit()
        logger.info(
            "Enriched song_artists for song %s: %s",
            song_id,
            [(n, r) for n, r in credits],
        )

    return {"status": "ok", "song_id": song_id}
