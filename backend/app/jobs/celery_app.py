# backend/app/jobs/celery_app.py
import logging
import multiprocessing

from celery import Celery  # type: ignore
from celery.signals import worker_ready  # type: ignore
from dotenv import load_dotenv

from app.config import get_config
from app.config.logging import setup_logging

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
    # A worker on more than one queue always checks them in sorted order, so
    # "lyrics" is emptied before "lyrics_backfill" (the default round-robin
    # would interleave them).
    broker_transport_options={"queue_order_strategy": "sorted"},
    # What a song needs before it can be sung (separation, lyrics) has a queue
    # and a worker of its own; everything else waits on "enrichment" and can
    # never hold them up. See celery_workers.sh.
    task_routes={
        "process_youtube_job": {"queue": "audio"},
        "process_audio_job": {"queue": "audio"},
        # Everything else defaults to the 'enrichment' queue
        "fetch_song_artwork": {"queue": "enrichment"},
        "detect_song_loudness": {"queue": "enrichment"},
        "detect_song_singing_map": {"queue": "enrichment"},
        "detect_song_vocal_range": {"queue": "enrichment"},
        "align_song_lyrics": {"queue": "lyrics"},
        "fingerprint_single_song": {"queue": "enrichment"},
        "enrich_song_artist_credits": {"queue": "enrichment"},
        "batch_fingerprint_songs": {"queue": "enrichment"},
        "batch_backfill_duration": {"queue": "enrichment"},
        "batch_backfill_vocal_range": {"queue": "enrichment"},
        "batch_backfill_loudness": {"queue": "enrichment"},
        "batch_backfill_singing_map": {"queue": "enrichment"},
        "batch_fetch_artist_images": {"queue": "enrichment"},
        "batch_fetch_albums": {"queue": "enrichment"},
        "batch_align_lyrics": {"queue": "enrichment"},
        "batch_rebuild_artist_credits": {"queue": "enrichment"},
    },
    task_default_queue="enrichment",
    **celery_logging_config,
)


@worker_ready.connect
def _fail_interrupted_jobs(sender, **kwargs):
    """A worker starting means its previous run is gone, along with any job it held."""
    from app.utils.cleanup_jobs import fail_interrupted_jobs

    try:
        fail_interrupted_jobs(sender.app.amqp.queues.consume_from.keys())
    except Exception:
        logger.error("Could not fail interrupted jobs", exc_info=True)
