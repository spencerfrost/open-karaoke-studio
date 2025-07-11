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
    "app", broker=broker_url, backend=result_backend, include=["app.jobs.jobs"]
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
    **celery_logging_config,
)


def init_celery(app):
    """Initialize Celery with Flask app context."""
    if not app:
        return celery

    class ContextTask(celery.Task):
        """Celery task with Flask application context."""

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
