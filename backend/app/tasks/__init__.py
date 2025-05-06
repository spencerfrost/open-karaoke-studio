"""
Asynchronous task handling for Open Karaoke Studio.
"""
from .celery_app import init_celery, celery
from .tasks import process_audio_task
