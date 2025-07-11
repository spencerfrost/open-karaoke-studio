#!/bin/bash
echo "Starting Open Karaoke Studio Celery Worker..."
source venv/bin/activate

# Configure environment variables safely
if [ -f .env ]; then
    echo "Loading environment from .env file..."
    set -a # automatically export all variables
    source .env
    set +a # stop automatically exporting
fi

# Ensure DATABASE_URL is set to the same value as the main app (backend directory)
export DATABASE_URL="sqlite:///karaoke.db"

# Set critical environment variables for PyTorch/CUDA compatibility
export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:128"
export CUDA_VISIBLE_DEVICES="0"
export OMP_NUM_THREADS="1" # Prevent OpenMP conflicts

# Display database URL
echo "Using database URL: $DATABASE_URL"

# Display broker URL if available
if [ ! -z "$CELERY_BROKER_URL" ]; then
    echo "Using broker URL: $CELERY_BROKER_URL"
fi

celery -A app.jobs.celery_app.celery worker \
    --loglevel=info \
    --concurrency=1 \
    --pool=threads
