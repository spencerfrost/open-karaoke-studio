# backend/app/jobs/celery_app.py
import logging
import multiprocessing

from app.config import get_config
from app.config.logging import setup_logging
from celery import Celery  # type: ignore
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

try:
    if multiprocessing.get_start_method(allow_none=True) != "spawn":
        multiprocessing.set_start_method("spawn", force=True)
except RuntimeError:
    pass

load_dotenv()
config = get_config()
logging_config = setup_logging(config)

broker_url = config.CELERY_BROKER_URL
result_backend = config.CELERY_RESULT_BACKEND

celery = Celery(
    "app",
    broker=broker_url,
    backend=result_backend,
    include=[
        "app.jobs.audio_tasks",
        "app.jobs.lyrics_tasks",
        "app.jobs.batch_tasks",
        "app.jobs.enrichment_tasks",
        "app.jobs.metadata_tasks",
    ],
)

celery_logging_config = logging_config.configure_celery_logging()
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    # Route heavy GPU/CPU audio jobs to their own queue so enrichment tasks
    # never compete with or block a separation job.
    task_routes={
        "process_youtube_job": {"queue": "audio"},
        "process_audio_job": {"queue": "audio"},
        # Everything else defaults to the 'enrichment' queue
        "fetch_song_artwork": {"queue": "enrichment"},
        "detect_song_loudness": {"queue": "enrichment"},
        "detect_song_vocal_range": {"queue": "enrichment"},
        "align_song_lyrics": {"queue": "lyrics"},
        "detect_song_chords": {"queue": "enrichment"},
        "fingerprint_single_song": {"queue": "enrichment"},
        "enrich_song_artist_credits": {"queue": "enrichment"},
        "batch_fingerprint_songs": {"queue": "enrichment"},
        "batch_backfill_artwork": {"queue": "enrichment"},
        "batch_backfill_duration": {"queue": "enrichment"},
        "batch_align_lyrics": {"queue": "enrichment"},
        "post_process_song": {"queue": "enrichment"},
    },
    task_default_queue="enrichment",
    **celery_logging_config,
)
