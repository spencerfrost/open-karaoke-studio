"""
Asynchronous job processing for Open Karaoke Studio.
"""

# Re-export the celery initialization function
from .celery_app import init_celery

__all__ = ["init_celery"]
