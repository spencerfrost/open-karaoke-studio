"""
Celery task definitions for audio processing
"""

import shutil
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Tuple

import librosa

from app.config.logging import get_structured_logger
from app.db.models import JobStatus
from app.repositories import JobRepository
from app.services import FileService, audio, file_management
from app.services.audio import create_audio_progress_mapper, detect_loudness, detect_vocal_range
from app.services.chord_detection_service import detect_chords
from app.services.separation_engines import (
    separate_with_clean_backing,
    separate_with_demucs,
    separate_with_hybrid,
    separate_with_roformer,
    separate_with_three_track,
)
from celery.utils.log import get_task_logger

from .celery_app import celery

logger = get_task_logger(__name__)
# Add structured logging for better job tracking
structured_logger = get_structured_logger(
    "app.jobs", {"job_module": "jobs", "component": "task_processor"}
)
job_repository = JobRepository()


def select_and_run_separation_engine(
    engine_type: str,
    input_path: Path,
    song_dir: Path,
    status_callback: Callable[[str], None],
    stop_event: threading.Event,
) -> Tuple[bool, Optional[float]]:
    """
    Select and run the appropriate audio separation engine.

    Args:
        engine_type: Engine to use ('roformer', 'hybrid', 'clean_backing', or 'demucs')
        input_path: Path to input audio file
        song_dir: Directory to write separated tracks
        status_callback: Callback for progress updates
        stop_event: Threading event to signal cancellation

    Returns:
        Tuple of (success: bool, detected_bpm: Optional[float])
    """
    logger.info("Using separation engine: %s", engine_type)

    # Map engine types to their separation functions
    engine_map = {
        "roformer": separate_with_roformer,
        "hybrid": separate_with_hybrid,
        "clean_backing": separate_with_clean_backing,
        "three_track": separate_with_three_track,
    }

    # Get separator function, defaulting to demucs
    separator_fn = engine_map.get(engine_type, separate_with_demucs)

    return separator_fn(
        input_path=input_path,
        song_dir=song_dir,
        status_callback=status_callback,
        stop_event=stop_event,
    )


def _broadcast_job_event(job, was_created=False):
    """
    Broadcast a job event via WebSocket if available.

    Args:
        job: The job object
        was_created: Whether this is a newly created job
    """
    # WebSocket broadcasting has been migrated to FastAPI
    # Job events are now handled by the FastAPI WebSocket server
    # Frontend polls the database via REST API for job status updates
    pass


class AudioProcessingError(Exception):
    """Custom exception for audio processing errors"""


def get_filepath_from_job(job):
    """Get the full filepath for a job based on its filename"""
    from pathlib import Path

    from app.config import get_config

    # Construct the path to the original file based on the job's filename
    config = get_config()
    song_dir = Path(config.BASE_LIBRARY_DIR) / job.song_id
    filepath = song_dir / "original.mp3"  # Or however you determine the filename

    return str(filepath)


@celery.task(bind=True, name="process_audio_job", max_retries=3)
def process_audio_job(self, job_id, engine_type="three_track"):
    """
    Celery task to process audio file

    Args:
        job_id: Unique identifier for the job
        engine_type: Separation engine to use ('demucs', 'roformer', 'hybrid')
    """
    logger.info("Starting audio processing job for job %s", job_id)

    # Get the job from storage with retry logic
    job_repository = JobRepository()
    job = job_repository.get_by_id(job_id)
    if not job:
        if self.request.retries < self.max_retries:
            logger.warning(
                "Job %s not found, retrying in %s seconds (attempt %s/%s)",
                job_id,
                2**self.request.retries,
                self.request.retries + 1,
                self.max_retries + 1,
            )
            # Exponential backoff: 2, 4, 8 seconds
            raise self.retry(countdown=2**self.request.retries)

        logger.error("Job %s not found after %s attempts", job_id, self.max_retries + 1)
        return {"status": "error", "message": "Job not found after retries"}

    # Determine the filepath from the job
    from pathlib import Path

    from app.config import get_config

    config = get_config()
    song_id = job.song_id
    if not song_id:
        logger.error("Job %s has no associated song_id", job_id)
        return {"status": "error", "message": "No song ID associated with job"}
    song_dir = Path(config.BASE_LIBRARY_DIR) / song_id
    filepath = song_dir / "original.mp3"
    filename = filepath.name

    # Update job status to processing
    job.status = JobStatus.PROCESSING
    job.started_at = datetime.now()
    job.engine_type = engine_type
    job_repository.update(job)

    # Create a stop event (for compatibility with audio.separate_audio)
    import threading

    stop_event = threading.Event()

    def update_progress(progress, message):
        """Update job progress and log the message.

        Uses throttling to prevent database spam during frequent updates.
        Only saves to database when progress changes significantly.
        """
        # Track the last saved progress to avoid unnecessary database writes
        last_saved_progress = getattr(update_progress, "_last_saved_progress", 0)

        job.progress = progress

        # Determine if we should save to database
        # Save if progress changed by 5% or more, or is a milestone
        progress_diff = abs(progress - last_saved_progress)
        is_milestone = progress in [0, 5, 25, 50, 75, 90, 100]
        should_save = progress_diff >= 5 or is_milestone

        # Update database only on milestones — skip entirely otherwise
        if should_save:
            job_repository.update(job)
            update_progress._last_saved_progress = progress

        if hasattr(self, "update_state"):
            self.update_state(
                state="PROGRESS",
                meta={
                    "job_id": job_id,
                    "filename": filename,
                    "progress": progress,
                    "status": "processing",
                    "message": message,
                },
            )
        # Enhanced logging with structured data - only for milestones
        if should_save:
            structured_logger.info(
                "Job progress: %s%% - %s",
                progress,
                message,
                extra={
                    "job_id": job_id,
                    "progress": progress,
                    "status": "processing",
                    "filename": filename,
                    "message": message,
                },
            )
        # Only log major progress milestones to reduce noise
        if progress % 25 == 0 or progress >= 95:
            logger.info("Job %s progress: %s%% - %s", job_id, progress, message)

    try:
        file_service = FileService()
        file_service.ensure_library_exists()
        config = get_config()
        song_id = job.song_id
        if not song_id:
            raise AudioProcessingError(f"Job {job_id} has no associated song_id")
        song_dir = Path(config.BASE_LIBRARY_DIR) / song_id
        update_progress(5, f"Created directory for {job_id}")

        # Separate audio using the selected engine
        success, _ = select_and_run_separation_engine(
            engine_type=engine_type,
            input_path=filepath,
            song_dir=song_dir,
            status_callback=lambda msg: update_progress(20, msg),
            stop_event=stop_event,
        )
        if not success:
            raise AudioProcessingError("Audio separation failed")

        # Update engine_type and duration — everything else goes to post_process_song
        from app.db.database import get_db_session
        from app.repositories.song_repository import SongRepository

        with get_db_session() as session:
            repo = SongRepository(session)
            update_kwargs = {"engine_type": engine_type}
            try:
                update_kwargs["duration"] = librosa.get_duration(path=str(filepath))
            except Exception as e:
                logger.warning("Duration detection failed for job %s: %s", job_id, e)
            repo.update(song_id, **update_kwargs)

        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.completed_at = datetime.now()
        job_repository.update(job)

        _broadcast_job_event(job)

        # Dispatch secondary enrichment task (fire-and-forget)
        celery.send_task("post_process_song", args=[song_id])
        logger.info("Dispatched post_process_song for song %s", song_id)

        return {
            "status": "success",
            "job_id": job_id,
            "filename": filename,
        }

    except audio.StopProcessingError:
        job.status = JobStatus.CANCELLED
        job.error = "Processing was manually stopped"
        job.completed_at = datetime.now()
        job_repository.update(job)
        # Use song_dir here which is based on song_id, not job_id
        if song_dir.exists():
            shutil.rmtree(song_dir)
        logger.info("Job %s was cancelled", job_id)
        return {"status": "cancelled", "job_id": job_id, "filename": filename}

    except Exception as e:
        error_message = str(e)
        logger.error("Error processing job %s: %s", job_id, error_message)
        traceback.print_exc()
        job.status = JobStatus.FAILED
        job.error = error_message
        job.completed_at = datetime.now()
        job_repository.update(job)
        return {
            "status": "error",
            "job_id": job_id,
            "filename": filename,
            "error": error_message,
        }


@celery.task(bind=True, name="cleanup_old_jobs")
def cleanup_old_jobs(self):
    """
    Periodically clean up old job records and temporary files
    """
    logger.info("Running job cleanup task")
    # Implement cleanup logic here


def _fetch_thumbnail_safe(
    youtube_service, video_id: str, song_id: str
) -> Optional[str]:
    """Fetch thumbnail in a background thread. Returns URL on success, None on failure."""
    try:
        url = youtube_service.fetch_and_save_thumbnail(video_id, song_id)
        logger.info("Background thumbnail download complete for video %s", video_id)
        return url
    except Exception as e:
        logger.warning("Background thumbnail download failed for %s: %s", video_id, e)
        return None


def _run_post_processing(song_id: str, song_dir: Path) -> None:
    """Run all enrichment steps after audio separation. Each step is independent — failures are logged only."""
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    vocals_path = song_dir / "vocals.mp3"
    instrumental_path = song_dir / "instrumental.mp3"
    update_kwargs = {}

    try:
        if vocals_path.exists():
            vocal_range = detect_vocal_range(
                vocals_path, lambda msg: logger.debug("VocalRange: %s", msg)
            )
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
            loudness_result = detect_loudness(
                instrumental_path, lambda msg: logger.debug("Loudness: %s", msg)
            )
            if loudness_result:
                update_kwargs["loudness_dbfs"] = loudness_result[0]
                update_kwargs["gain_db"] = loudness_result[1]
    except Exception as e:
        logger.warning("Loudness detection failed for song %s: %s", song_id, e)

    # Fetch album art (iTunes first, YouTube thumbnail as fallback)
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

    # AcoustID fingerprinting — identify the track by audio content
    # Prefer original.mp3 (full mix) — stems are acoustically degraded and produce unreliable matches
    try:
        original_path = song_dir / "original.mp3"
        audio_path = (
            original_path if original_path.exists()
            else instrumental_path if instrumental_path.exists()
            else vocals_path
        )
        if audio_path.exists():
            from app.services.acoustid_service import AcoustIdService

            with get_db_session() as session:
                repo = SongRepository(session)
                AcoustIdService(repo).fingerprint_and_identify(song_id, audio_path)
        else:
            logger.warning("AcoustID: no audio file found for song %s", song_id)
    except Exception:
        logger.warning("AcoustID fingerprinting failed for song %s", song_id, exc_info=True)

    # Populate song_artists join table (regex-based; AcoustID may overwrite if it auto-corrects)
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
    Fire-and-forget enrichment task dispatched after audio separation completes.

    Runs vocal range detection, chord detection, loudness normalization, and
    thumbnail download. No Job record — failures are logged only.
    """
    logger.info("Starting post-processing for song %s", song_id)

    from pathlib import Path

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


@celery.task(name="batch_fingerprint_songs")
def batch_fingerprint_songs(reprocess_all: bool = False) -> None:
    """
    Batch Celery task: fingerprint songs via AcoustID.
    By default only processes songs with status='not_checked'.
    Pass reprocess_all=True to re-fingerprint every song (clears prior results).
    """
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
    """
    Batch Celery task: backfill album art for songs missing it.
    By default only processes songs with album_id IS NULL.
    Pass force=True to reprocess every song.
    """
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
        # Baseline delay to stay well under the iTunes rate limit
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


@celery.task(name="batch_backfill_genres")
def batch_backfill_genres(mode: str = "missing") -> dict:
    """
    Batch Celery task: populate genres from Last.fm for library songs.

    mode="missing" — only processes songs where genres is NULL or empty.
    mode="all"     — processes every song in the library.

    Skips songs where Last.fm returns no matches (leaves existing value unchanged).
    """
    import asyncio

    from app.db.database import get_db_session
    from app.db.models.song import DbSong
    from app.repositories.song_repository import SongRepository
    from app.services.lastfm_service import fetch_track_genres

    with get_db_session() as session:
        query = session.query(DbSong.id, DbSong.title, DbSong.artist)
        if mode == "missing":
            query = query.filter(
                (DbSong.genres.is_(None)) | (DbSong.genres == [])
            )
        rows = query.all()

    songs = [(row[0], row[1], row[2]) for row in rows]
    logger.info("batch_backfill_genres: processing %d songs (mode=%s)", len(songs), mode)

    success = 0
    skipped = 0
    for song_id, title, artist in songs:
        if not title or not artist:
            skipped += 1
            continue
        try:
            genres = asyncio.run(fetch_track_genres(artist, title))
            if genres:
                with get_db_session() as session:
                    SongRepository(session).update(song_id, genres=genres)
                success += 1
            else:
                skipped += 1
        except Exception:
            logger.warning("batch_backfill_genres: error for song %s", song_id, exc_info=True)
            skipped += 1

    logger.info(
        "batch_backfill_genres: done — %d updated, %d skipped", success, skipped
    )
    return {"processed": len(songs), "success": success, "skipped": skipped}


@celery.task(name="batch_backfill_duration")
def batch_backfill_duration(mode: str = "missing") -> dict:
    """
    Batch Celery task: populate duration from the original audio file.

    mode="missing" — only processes songs where duration IS NULL.
    mode="all"     — processes every song in the library.
    """
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


@celery.task(name="fingerprint_single_song")
def fingerprint_single_song(song_id: str) -> dict:
    """Fingerprint a single song via AcoustID."""
    from pathlib import Path

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

    return {"status": "ok", "song_id": song_id}


@celery.task(name="enrich_song_artist_credits")
def enrich_song_artist_credits(song_id: str) -> dict:
    """Re-resolve artist credits for a single song using MB recording → MB search → regex."""
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

        # If MB/regex left a single primary with "&", try heuristic DB-based split
        credits = try_ampersand_split(credits, session)

        artist_repo = ArtistRepository(session)

        # Clear existing links
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


@celery.task(bind=True, name="process_youtube_job", max_retries=3)
def process_youtube_job(self, job_id, video_id, metadata, engine_type="three_track"):
    """
    Unified task for processing YouTube videos from start to finish

    Args:
        job_id: Job identifier
        video_id: YouTube video ID
        metadata: Dict with artist, title, album, etc.
        engine_type: Separation engine to use ('demucs', 'roformer', 'hybrid')
    """
    logger.info(
        "Starting unified YouTube processing job for job %s (artist: %s, title: %s, video_id: %s)",
        job_id,
        metadata.get("artist"),
        metadata.get("title"),
        video_id,
    )

    # Get the job from storage using repository
    job_repository = JobRepository()
    job = job_repository.get_by_id(job_id)
    if not job:
        logger.error("Job %s not found for video_id %s", job_id, video_id)
        return {"status": "error", "message": "Job not found"}

    # Get the song_id from the job
    song_id = job.song_id
    if not song_id:
        logger.error("Job %s has no associated song_id", job_id)
        return {"status": "error", "message": "No song ID associated with job"}

    # Verify the song exists
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    with get_db_session() as session:
        repo = SongRepository(session)
        db_song = repo.fetch(song_id)
    if not db_song:
        logger.error("Song %s not found for job %s", song_id, job_id)
        # Mark job as failed
        job.status = JobStatus.FAILED
        job.error = f"Song {song_id} not found in database"
        job.completed_at = datetime.now()
        job_repository.update(job)
        return {"status": "error", "message": f"Song {song_id} not found"}

    # Update job status to downloading
    job.status = JobStatus.DOWNLOADING
    job.status_message = "Downloading video from YouTube"
    job.started_at = datetime.now()
    job.progress = 5
    job.engine_type = engine_type
    job_repository.update(job)

    def update_progress(progress, message, status=None):
        """Update job progress and status.

        Uses throttling to prevent database spam during frequent updates.
        Only saves to database when progress changes significantly or status changes.
        """
        # Track the last saved progress to avoid unnecessary database writes
        last_saved_progress = getattr(update_progress, "_last_saved_progress", 0)
        last_saved_status = getattr(update_progress, "_last_saved_status", None)

        job.progress = progress
        job.status_message = message
        if status:
            job.status = status

        # Determine if we should save to database
        # Save if: status changed, progress changed by 5% or more, or is a milestone
        progress_diff = abs(progress - last_saved_progress)
        status_changed = status and status != last_saved_status
        # Updated milestones to include more checkpoints during audio processing (30-90% range)
        is_milestone = progress in [
            0,
            5,
            25,
            30,
            35,
            40,
            50,
            60,
            70,
            75,
            80,
            85,
            90,
            95,
            100,
        ]
        should_save = status_changed or progress_diff >= 5 or is_milestone

        # Update database only on milestones or status changes — skip entirely otherwise
        if should_save:
            job_repository.update(job)
            update_progress._last_saved_progress = progress
            update_progress._last_saved_status = job.status

        if hasattr(self, "update_state"):
            self.update_state(
                state="PROGRESS",
                meta={
                    "job_id": job_id,
                    "progress": progress,
                    "status": job.status.value,
                    "message": message,
                },
            )
        # Only log major progress milestones to reduce noise
        if progress % 25 == 0 or progress >= 95:
            logger.info("Job %s: %s%% - %s", job_id, progress, message)

    try:
        # Phase 1: Download (5-30% progress)
        from pathlib import Path

        from app.config import get_config
        from app.services.youtube_service import YouTubeService

        config = get_config()
        youtube_service = YouTubeService()
        file_service = FileService()
        file_service.ensure_library_exists()

        song_id = job.song_id
        if not song_id:
            raise AudioProcessingError(f"Job {job_id} has no associated song_id")
        song_dir = Path(config.BASE_LIBRARY_DIR) / song_id

        update_progress(10, "Starting YouTube download")

        youtube_service.download_video(
            video_id_or_url=video_id,
            song_id=song_id,
            artist=metadata.get("artist"),
            title=metadata.get("title"),
        )

        update_progress(
            30,
            f"Download complete, preparing {engine_type} engine",
            JobStatus.PROCESSING,
        )

        # Phase 2: Audio Processing (30-90% progress)
        original_file = song_dir / "original.mp3"

        if not original_file.exists():
            raise AudioProcessingError(
                f"Original audio file not found: {original_file}"
            )

        import threading

        stop_event = threading.Event()

        update_progress(35, f"Initializing {engine_type} audio processing")

        audio_progress_callback = create_audio_progress_mapper(
            engine_type=engine_type,
            base_start=35,
            base_end=90,
            update_fn=lambda prog, msg: update_progress(
                prog, f"Audio processing: {msg}"
            ),
        )

        success, _ = select_and_run_separation_engine(
            engine_type=engine_type,
            input_path=original_file,
            song_dir=song_dir,
            status_callback=audio_progress_callback,
            stop_event=stop_event,
        )
        if not success:
            raise AudioProcessingError("Audio separation failed")

        # Update engine_type and duration — everything else goes to post_process_song
        try:
            with get_db_session() as session:
                repo = SongRepository(session)
                update_fields = {"engine_type": engine_type}
                try:
                    update_fields["duration"] = librosa.get_duration(
                        path=str(original_file)
                    )
                except Exception as e:
                    logger.warning("Duration detection failed for song %s: %s", song_id, e)
                repo.update(song_id, **update_fields)
        except Exception as e:
            logger.error("Error updating song metadata for song %s: %s", song_id, e)

        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.status_message = "Processing complete"
        job.completed_at = datetime.now()
        job_repository.update(job)

        _broadcast_job_event(job)

        # Dispatch secondary enrichment task (fire-and-forget)
        celery.send_task("post_process_song", args=[song_id])
        logger.info("Dispatched post_process_song for song %s", song_id)

        return {
            "status": "success",
            "job_id": job_id,
            "song_id": song_id,
        }

    except audio.StopProcessingError:
        job.status = JobStatus.CANCELLED
        job.error = "Processing was manually stopped"
        job.completed_at = datetime.now()
        job_repository.update(job)
        if song_dir.exists():
            shutil.rmtree(song_dir)
        logger.info("Job %s was cancelled", job_id)
        return {"status": "cancelled", "job_id": job_id}

    except Exception as e:
        error_message = str(e)
        logger.error("Error processing YouTube job %s: %s", job_id, error_message)
        traceback.print_exc()
        job.status = JobStatus.FAILED
        job.error = error_message
        job.completed_at = datetime.now()
        job_repository.update(job)
        return {"status": "error", "job_id": job_id, "error": error_message}


# Event system integration
def _handle_job_event(event):
    """
    Handle job events from the event system.

    This replaces the direct function calls from models.
    """
    try:
        from app.db.models import Job, JobStatus
        from app.utils.events import JobEvent

        if isinstance(event, JobEvent):
            # Reconstruct job object from event data
            job_data = event.job_data
            job = Job(
                id=job_data["id"],
                filename=job_data.get("filename", ""),
                status=JobStatus(job_data["status"]),
                title=job_data.get("title"),
                artist=job_data.get("artist"),
                status_message=job_data.get(
                    "message"
                ),  # Use status_message instead of message
                progress=job_data.get("progress", 0),
                error=job_data.get("error"),
                task_id=job_data.get("task_id"),
                song_id=job_data.get("song_id"),
                notes=job_data.get("notes"),
                created_at=job_data.get("created_at"),
                started_at=job_data.get("started_at"),
                completed_at=job_data.get("completed_at"),
                dismissed=job_data.get("dismissed", False),
            )

            # Use the existing broadcast function
            _broadcast_job_event(job, event.was_created)

    except Exception as e:
        logger.error("Error handling job event: %s", e, exc_info=True)


# Subscribe to job events when module is imported
def _setup_event_subscriptions():
    """Set up event subscriptions for the jobs module."""
    try:
        from app.utils.events import subscribe_to_job_events

        subscribe_to_job_events(_handle_job_event)
        logger.info("Jobs module subscribed to job events")
    except Exception as e:
        logger.error("Failed to set up job event subscriptions: %s", e)


# Set up subscriptions when module loads
_setup_event_subscriptions()
