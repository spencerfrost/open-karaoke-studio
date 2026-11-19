"""Send a song's enrichment steps, at most one queue-time run per step.

A step is a batch job with a per-song task (app.services.batch_jobs). Two
callers send one: a song's own pipeline, which always wants it run, and the
queue-time update (app.jobs.song_updates), which only wants it when nothing
is already on the way. A Redis key per song and step, set when the step is
sent and removed when it finishes, is how the second one knows.
"""

import logging
from functools import lru_cache

from .celery_app import celery

logger = logging.getLogger(__name__)

# How long a sent step counts as on the way if nothing removes its key: a
# worker that died mid-step, or a broker that lost the message.
IN_FLIGHT_SECONDS = 60 * 60


@lru_cache(maxsize=1)
def _redis():
    """The broker's Redis, so the keys live where the tasks do."""
    import redis

    from app.config import get_config

    return redis.Redis.from_url(
        get_config().CELERY_BROKER_URL, socket_connect_timeout=2, socket_timeout=2
    )


def _key(kind: str, song_id: str) -> str:
    return f"song-step:{kind}:{song_id}"


def send_song_step(kind: str, song_id: str, *, force: bool = False) -> bool:
    """Queue update_song_step for one step of one song; returns whether it was sent.

    Without `force`, a step already queued or running for the song isn't sent
    again, and the task checks the song still needs it when it starts. With
    `force` (the song's own pipeline, whose audio or lyrics just changed) it
    is always sent and always runs.
    """
    key = _key(kind, song_id)
    if force:
        _redis().set(key, 1, ex=IN_FLIGHT_SECONDS)
    elif not _redis().set(key, 1, nx=True, ex=IN_FLIGHT_SECONDS):
        return False
    try:
        celery.send_task(
            "update_song_step", args=[kind, song_id], kwargs={"force": force}
        )
    except Exception:
        step_finished(kind, song_id)
        raise
    return True


def step_finished(kind: str, song_id: str) -> None:
    """The step is no longer on the way. Never raises: the key expires anyway."""
    try:
        _redis().delete(_key(kind, song_id))
    except Exception:
        logger.warning(
            "Couldn't clear the in-flight mark for %s on song %s",
            kind,
            song_id,
            exc_info=True,
        )
