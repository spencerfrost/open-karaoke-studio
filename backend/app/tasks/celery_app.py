# backend/app/tasks/celery_app.py
from celery import Celery
import os
import multiprocessing
from dotenv import load_dotenv
import logging

# Setup logging
logger = logging.getLogger(__name__)

try:
    if multiprocessing.get_start_method(allow_none=True) != 'spawn':
        multiprocessing.set_start_method('spawn', force=True)
    logger.info("Multiprocessing start method set to 'spawn' for CUDA compatibility")
except RuntimeError as e:
    logger.warning(f"Could not set multiprocessing start method: {e}")

load_dotenv()

# Get broker and backend URLs from environment with fallbacks
broker_url = os.getenv('CELERY_BROKER_URL', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
result_backend = os.getenv('CELERY_RESULT_BACKEND', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

logger.info(f"Configuring Celery with broker: {broker_url}, backend: {result_backend}")

# Create Celery app - this name is what forms the beginning of task names
celery = Celery(
    'app',
    broker=broker_url,
    backend=result_backend,
    include=['app.tasks.tasks']
)

# Configure Celery
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    task_routes={
        'app.tasks.tasks.process_audio_task': {'queue': 'audio_processing'},
        'app.tasks.tasks.cleanup_old_jobs': {'queue': 'maintenance'},
    }
)

# For Flask integration (optional)
def init_celery(app):
    """Initialize Celery with Flask app context."""
    if not app:
        return celery

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery