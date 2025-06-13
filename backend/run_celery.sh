#!/bin/bash
echo "Starting Open Karaoke Studio Celery Worker..."
source venv/bin/activate

# Configure environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

export $(grep -v '^#' .env | xargs -0 2>/dev/null)

# Ensure DATABASE_URL is set to the same value as the main app (backend directory)
export DATABASE_URL="sqlite:///karaoke.db"

# Display database URL
echo "Using database URL: $DATABASE_URL"

# Display broker URL if available
if [ ! -z "$CELERY_BROKER_URL" ]; then
    echo "Using broker URL: $CELERY_BROKER_URL"
fi

celery -A app.jobs.celery_app.celery worker \
    --loglevel=info \
    --concurrency=1 \
    --pool=solo