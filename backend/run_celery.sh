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
#
# Each worker runs in a restart loop. A native crash (a segfault in CUDA code)
# kills the process outright, and without the loop its queue would sit unserved
# until someone noticed. On start, a worker fails the jobs its last run was
# holding (see app/utils/cleanup_jobs.py).
run_worker() {
    local name="$1"
    shift
    while true; do
        celery -A app.jobs.celery_app.celery worker \
            --loglevel=info \
            --pool=threads \
            --hostname="$name@%h" \
            --without-gossip \
            --without-mingle \
            "$@"
        echo "Celery worker '$name' exited with status $?; restarting in 5s..."
        sleep 5
    done
}

# Ctrl-C or SIGTERM stops everything: the restart loops and the workers, which
# share this script's process group. The loops die before the workers finish
# their warm shutdown, so nothing restarts.
shutdown() {
    trap '' INT TERM
    kill -TERM 0 2>/dev/null
    wait
}
trap shutdown INT TERM

# Worker 1: heavy audio processing — concurrency=1 ensures only one separation job runs at a time
run_worker audio --concurrency=1 --queues=audio &

# Worker 2: enrichment tasks — concurrency=3 allows parallel post-processing
# while leaving room for a dedicated lyrics worker.
run_worker enrichment --concurrency=3 --queues=enrichment &

# Worker 3: lyrics alignment gets dedicated capacity so it cannot sit behind
# artwork, fingerprinting, or chord detection.
run_worker lyrics --concurrency=1 --queues=lyrics &

wait
