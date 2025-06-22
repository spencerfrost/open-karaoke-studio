# backend/app/jobs/celery_app.py
import logging
import multiprocessing

from celery import Celery
from dotenv import load_dotenv

from ..config import get_config  # pylint: disable=wrong-import-position
from ..config.logging import setup_logging  # pylint: disable=wrong-import-position

# Setup logging first
logger = logging.getLogger(__name__)

try:
    if multiprocessing.get_start_method(allow_none=True) != "spawn":
        multiprocessing.set_start_method("spawn", force=True)
except RuntimeError:
    pass  # Method already set, ignore

load_dotenv()

# Import configuration for centralized settings

config = get_config()

# Setup logging for Celery
logging_config = setup_logging(config)

# Use centralized configuration
broker_url = config.CELERY_BROKER_URL
result_backend = config.CELERY_RESULT_BACKEND

# Create Celery app - this name is what forms the beginning of task names
celery = Celery("app", broker=broker_url, backend=result_backend, include=["app.jobs.jobs"])

# Configure Celery with enhanced logging
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


# For Flask integration (optional)
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
