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

# Ensure DATABASE_URL is set — must come from .env or the environment
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL is not set. Add it to your .env file."
    exit 1
fi

# Set critical environment variables for PyTorch/CUDA compatibility
export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:128"
export CUDA_VISIBLE_DEVICES="0"
export GPU_IDLE_CLEANUP_SECONDS="${GPU_IDLE_CLEANUP_SECONDS:-1800}"
export OMP_NUM_THREADS="1" # Prevent OpenMP conflicts

# Display database URL
echo "Using database URL: $DATABASE_URL"

# Display broker URL if available
if [ ! -z "$CELERY_BROKER_URL" ]; then
    echo "Using broker URL: $CELERY_BROKER_URL"
fi

# All three workers run --without-gossip --without-mingle: they're single-box,
# not a cluster, so cross-worker discovery isn't needed — and gossip's heartbeat
# checks are what were logging "missed heartbeat" warnings whenever a heavy
# synchronous task (e.g. batch_align_lyrics) starved the GIL on this shared box.

# Worker 1: heavy audio processing — concurrency=1 ensures only one separation job runs at a time
celery -A app.jobs.celery_app.celery worker \
    --loglevel=info \
    --concurrency=1 \
    --pool=threads \
    --queues=audio \
    --hostname=audio@%h \
    --without-gossip \
    --without-mingle &

# Worker 2: enrichment tasks — concurrency=3 allows parallel post-processing
# while leaving room for a dedicated lyrics worker.
celery -A app.jobs.celery_app.celery worker \
    --loglevel=info \
    --concurrency=3 \
    --pool=threads \
    --queues=enrichment \
    --hostname=enrichment@%h \
    --without-gossip \
    --without-mingle &

# Worker 3: lyrics alignment gets dedicated capacity so it cannot sit behind
# artwork, fingerprinting, or chord detection.
celery -A app.jobs.celery_app.celery worker \
    --loglevel=info \
    --concurrency=1 \
    --pool=threads \
    --queues=lyrics \
    --hostname=lyrics@%h \
    --without-gossip \
    --without-mingle &

wait
