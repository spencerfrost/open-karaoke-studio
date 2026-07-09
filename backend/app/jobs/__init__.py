"""
Asynchronous job processing for Open Karaoke Studio.
"""

from .celery_app import celery

__all__ = ["celery"]
