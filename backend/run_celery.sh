#!/bin/bash
echo "Starting Open Karaoke Studio Celery Worker..."
source venv/bin/activate

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

export $(grep -v '^#' .env | xargs -0 2>/dev/null)

echo "Using broker URL: $CELERY_BROKER_URL"
cd .. && celery -A backend.app.celery_app.celery worker \
    --loglevel=info \
    --concurrency=1 \
    --pool=solo