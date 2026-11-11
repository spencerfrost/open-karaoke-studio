"""Metadata and enrichment Celery tasks."""

from pathlib import Path
from typing import Optional, cast

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
    Shared by the per-song pipeline task and the library-wide backfill. "ok"
    and "silent" are answers, and save the version that reached them.
    """
    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.processing_versions import LOUDNESS_VERSION

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
        with get_db_session() as session:
            SongRepository(session).update(song_id, loudness_version=LOUDNESS_VERSION)
        return "silent"

    with get_db_session() as session:
        SongRepository(session).update(
            song_id,
            loudness_lufs=result.loudness_lufs,
            true_peak_dbtp=result.true_peak_dbtp,
            gain_db=result.gain_db,
            loudness_version=LOUDNESS_VERSION,
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
    from app.services.processing_versions import SINGING_MAP_VERSION
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
        SongRepository(session).update(
            song_id,
            singing_map=json.dumps(singing_map),
            singing_map_version=SINGING_MAP_VERSION,
        )
    return "ok"


@celery.task(name="detect_song_singing_map")
def detect_song_singing_map(song_id: str) -> dict:
    """Measure when the separated lead and backing vocals are singing."""
    logger.info("[PIPELINE] detect_song_singing_map starting for song %s", song_id)
    status = detect_and_store_singing_map(song_id)
    if status == "ok":
        queue_vocal_range_if_ready(song_id)
    return {"status": status, "song_id": song_id}


def detect_and_store_vocal_range(song_id: str) -> str:
    """Measure a song's vocal range from vocals.mp3 and save it.

    Returns "ok" (a range), "labelled" (no sung range, and why: rapped, no
    lead found, one note), "no_range" (no note held long enough), "waiting"
    (no singing map yet: the map's task queues this once it's measured),
    "no_audio", or "error". Shared by the per-song pipeline task, the
    library-wide backfill and the admin "analyze" endpoint. "ok", "labelled"
    and "no_range" are answers: they replace the stored range, even with
    none, and save the version that reached them.
    """
    import json
    from datetime import datetime, timezone

    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.processing_versions import VOCAL_RANGE_VERSION
    from app.services.vocal_range import context_for, lyrics_md5

    vocals_path = Path(get_config().BASE_LIBRARY_DIR) / song_id / "vocals.mp3"
    if not vocals_path.exists():
        logger.warning("detect_vocal_range: vocals.mp3 not found for song %s", song_id)
        return "no_audio"

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if song is None:
            return "no_audio"
        context = context_for(song)
        measured_lyrics = lyrics_md5(cast(Optional[str], song.synced_lyrics))
    if context is None:
        logger.info("detect_vocal_range: song %s has no singing map yet", song_id)
        return "waiting"

    try:
        result = detect_vocal_range(
            vocals_path, context, lambda msg: logger.debug("VocalRange: %s", msg)
        )
    except Exception:
        logger.warning("detect_vocal_range: failed for song %s", song_id, exc_info=True)
        return "error"

    detail = {
        **result["detail"],
        "label": result["label"],
        "lyrics_md5": measured_lyrics,
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with get_db_session() as session:
        SongRepository(session).update(
            song_id,
            vocal_range_low=result["low"],
            vocal_range_high=result["high"],
            vocal_range_detail=json.dumps(detail),
            vocal_range_version=VOCAL_RANGE_VERSION,
        )

    if result["low"] is not None:
        logger.info(
            "detect_vocal_range: %s-%s for song %s",
            result["low"],
            result["high"],
            song_id,
        )
        return "ok"
    logger.info(
        "detect_vocal_range: no range for song %s (%s)",
        song_id,
        result["label"] or "no held notes",
    )
    return "labelled" if result["label"] else "no_range"


def queue_vocal_range_if_ready(song_id: str) -> bool:
    """Queue the song's vocal range once both its inputs are in.

    The range reads the singing map and the synced lyrics' line times, which
    two other tasks produce; each calls this when it finishes, and whichever
    finishes second queues the range. Lyrics count as in once alignment has
    reached an answer (word_timing_version is set), "no lyrics" included. A
    range that's already up to date for these lyrics isn't measured again.

    Never raises: the caller's own result is already saved, and a song left
    without a range is caught by the queue-time update or the backfill.
    """
    try:
        return _queue_vocal_range_if_ready(song_id)
    except Exception:
        logger.warning(
            "Couldn't queue the vocal range for song %s", song_id, exc_info=True
        )
        return False


def _queue_vocal_range_if_ready(song_id: str) -> bool:
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.vocal_range import is_out_of_date

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        ready = (
            song is not None
            and song.singing_map is not None
            and song.word_timing_version is not None
            and is_out_of_date(song)
        )
    if ready:
        celery.send_task("detect_song_vocal_range", args=[song_id])
    return ready


@celery.task(name="detect_song_vocal_range")
def detect_song_vocal_range(song_id: str) -> dict:
    """Measure the lead singer's range from vocals.mp3 and store it."""
    logger.info("[PIPELINE] detect_song_vocal_range starting for song %s", song_id)
    return {"status": detect_and_store_vocal_range(song_id), "song_id": song_id}


def detect_and_store_album_art_video(song_id: str) -> str:
    """Mark whether a song's video is an album track upload.

    Reads the info yt-dlp saved beside the download; a song without one asks
    YouTube again. Returns "album_art" or "own_picture", and raises when it
    can't tell. Shared by the per-song task and the library-wide backfill.
    """
    import json

    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.youtube_service import YouTubeService, is_album_art_upload

    info_path = Path(get_config().BASE_LIBRARY_DIR) / song_id / "original.info.json"
    if info_path.exists():
        info = json.loads(info_path.read_text(encoding="utf-8"))
    else:
        with get_db_session() as session:
            song = SongRepository(session).fetch(song_id)
            video_id = song.video_id if song else None
        if not video_id:
            raise ValueError("song has no video")
        info = YouTubeService().extract_video_info(video_id)
    album_art = is_album_art_upload(info)
    with get_db_session() as session:
        SongRepository(session).update(song_id, video_is_album_art=album_art)
    return "album_art" if album_art else "own_picture"


@celery.task(name="detect_song_album_art_video")
def detect_song_album_art_video(song_id: str) -> dict:
    """Mark whether the song's video is just its album cover over the audio."""
    try:
        status = detect_and_store_album_art_video(song_id)
    except Exception:
        logger.warning(
            "detect_song_album_art_video: failed for song %s", song_id, exc_info=True
        )
        status = "error"
    return {"status": status, "song_id": song_id}


@celery.task(name="update_song_step")
def update_song_step(kind: str, song_id: str) -> dict:
    """Run one batch job's per-song task for a song, if the song still needs it.

    Queued when a song is added to a session's queue (app.jobs.song_updates).
    Checking again here means a song queued twice in a row is done once.
    """
    from app.db.database import get_db_session
    from app.services.batch_jobs import get_job, song_needs

    job = get_job(kind)
    if job.song_task is None:
        raise ValueError(f"{kind} has no per-song task")
    with get_db_session() as session:
        if not song_needs(session, job, song_id):
            return {"status": "up_to_date", "kind": kind, "song_id": song_id}
    logger.info("update_song_step: %s for queued song %s", kind, song_id)
    return celery.tasks[job.song_task](song_id)


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
