"""
Celery configuration for task queue management
"""
from celery import Celery
import os
from dotenv import load_dotenv

# Load environment variables if available
load_dotenv()

# Configure Celery
def make_celery(app=None):
    # Default Redis URL or from environment
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    celery = Celery(
        'open_karaoke',
        broker=redis_url,
        backend=redis_url,
        include=['app.tasks'],
        broker_connection_retry_on_startup=True,
        broker_connection_max_retries=1
    )
    
    # Set some default configuration
    celery.conf.update(
        result_expires=3600,  # Results expire after 1 hour
        task_track_started=True,
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
    )
    
    # If we have a Flask app, configure it properly
    if app:
        TaskBase = celery.Task
        
        class ContextTask(TaskBase):
            abstract = True
            
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return TaskBase.__call__(self, *args, **kwargs)
        
        celery.Task = ContextTask
        
    return celery

# Create the Celery instance
celery = make_celery()
