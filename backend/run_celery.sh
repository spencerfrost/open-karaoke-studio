#!/bin/bash
echo "Starting Open Karaoke Studio Celery Worker..."
source venv/bin/activate

# Start the Celery worker with the configuration file
celery -A app.celery_app.celery worker \
    --loglevel=info \
    --concurrency=2
