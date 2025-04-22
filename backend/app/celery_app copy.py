# backend/app/celery_app.py
from celery import Celery
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
logger.warning(f"Celery instance in celery_app.py using Broker/Backend URL: {redis_url}")

# --- Create the Celery instance WITH broker/backend config ---
celery = Celery(
    'open_karaoke',
    broker=redis_url,      # SET BROKER HERE
    backend=redis_url,     # SET BACKEND HERE
    include=['app.tasks']  # Your tasks module
    # Add other static config like broker_connection_retry_on_startup if needed
)
def init_celery(app):
    """Configure Celery using the Flask app's configuration."""
    # Set Broker and Backend URLs primarily from Flask config
    broker_url = app.config.get('CELERY_BROKER_URL', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
    result_backend = app.config.get('CELERY_RESULT_BACKEND', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

    logger.warning(f"Initializing Celery. Attempting Broker: {broker_url}, Backend: {result_backend}")

    celery.conf.update(
        broker_url=broker_url,
        result_backend=result_backend,
        # --- Add other configurations from app.config or defaults ---
        # Example pulling from Flask config (if you set app.config['CELERY_RESULT_EXPIRES'] = 3600)
        result_expires=app.config.get('CELERY_RESULT_EXPIRES', 3600),
        task_track_started=app.config.get('CELERY_TASK_TRACK_STARTED', True),
        task_serializer=app.config.get('CELERY_TASK_SERIALIZER', 'json'),
        accept_content=app.config.get('CELERY_ACCEPT_CONTENT', ['json']),
        result_serializer=app.config.get('CELERY_RESULT_SERIALIZER', 'json'),
        timezone=app.config.get('CELERY_TIMEZONE', 'UTC'),
        enable_utc=app.config.get('CELERY_ENABLE_UTC', True),
        # Add connection retry settings here too
        broker_connection_retry_on_startup=True,
        # Pull relevant settings from your celery.conf notes into Flask config
        worker_prefetch_multiplier = app.config.get('CELERY_WORKER_PREFETCH_MULTIPLIER', 1),
        task_acks_late = app.config.get('CELERY_TASK_ACKS_LATE', True),
    )

    # --- Log the final configuration Celery will use ---
    logger.info(f"Celery Initialized. Final Broker URL: {celery.conf.broker_url}")
    logger.info(f"Celery Initialized. Final Result Backend: {celery.conf.result_backend}")


    # Optional: Uncomment to add Flask app context to tasks if needed
    # TaskBase = celery.Task
    # class ContextTask(TaskBase):
    #     abstract = True
    #     def __call__(self, *args, **kwargs):
    #         with app.app_context():
    #             return TaskBase.__call__(self, *args, **kwargs)
    # celery.Task = ContextTask

# Note: We export 'celery' instance and 'init_celery' function.
# 'celery' is the actual Celery application object.