"""
Asynchronous job processing for Open Karaoke Studio.
"""
from .celery_app import init_celery, celery
from .jobs import process_audio_job
