#!/bin/bash
# The Celery workers, for dev (run_celery.sh) and the prod container alike.
#
# What a song needs before it can be sung gets a worker of its own, so it never
# waits behind anything else:
#   audio       download + separation (GPU)
#   lyrics      alignment and transcription (GPU); library-wide runs wait on
#               lyrics_backfill, which this worker only takes from when
#               "lyrics" is empty (see queue_order_strategy in celery_app.py)
#   enrichment  everything that can finish after the song is playable: artwork,
#               fingerprint, lyrics prefetch, vocal range, loudness, singing
#               map, credits, batch jobs
#
# --disable-prefetch: a worker takes a task only when it has a free slot, so a
# low-priority task is never held in reserve ahead of one that arrives later.
#
# --without-gossip --without-mingle: single box, not a cluster, so cross-worker
# discovery isn't needed, and gossip's heartbeat checks logged "missed
# heartbeat" warnings whenever a heavy synchronous task starved the GIL.
#
# Each worker runs in a restart loop. A native crash (a segfault in CUDA code)
# kills the process outright, and without the loop its queue would sit unserved
# until someone noticed. On start, a worker fails the jobs its last run was
# holding (see app/utils/cleanup_jobs.py).

cd "$(dirname "$0")" || exit 1

LOG_LEVEL="${CELERY_LOG_LEVEL:-info}"

run_worker() {
    local name="$1"
    shift
    while true; do
        celery -A app.jobs.celery_app.celery worker \
            --loglevel="$LOG_LEVEL" \
            --pool=threads \
            --hostname="$name@%h" \
            --without-gossip \
            --without-mingle \
            --disable-prefetch \
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

# One separation at a time on the GPU.
run_worker audio --concurrency=1 --queues=audio &

# One alignment at a time on the GPU; queue order is priority order.
run_worker lyrics --concurrency=1 --queues=lyrics,lyrics_backfill &

# Mostly network and CPU work, so a few at once.
run_worker enrichment --concurrency=3 --queues=enrichment &

wait
