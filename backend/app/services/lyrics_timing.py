import logging
from datetime import datetime
from pathlib import Path
from typing import Any

# Routed to logs/lyrics_timing.jsonl by the "app.services.lyrics_timing" entry in
# app/config/logging.py. Keep a plain logger: a LoggerAdapter replaces `extra`
# and drops the event fields.
logger = logging.getLogger(__name__)

# Passing one of these in `extra` makes logging raise KeyError.
_RESERVED_RECORD_KEYS = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__
) | {"message", "asctime"}


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_normalize_value(item) for item in value]
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_value(item) for key, item in value.items()}
    return value


def log_lyrics_event(song_id: str, event: str, **fields: Any) -> None:
    payload = {
        "song_id": song_id,
        "event": event,
    }
    for key, value in fields.items():
        if key in _RESERVED_RECORD_KEYS:
            key = f"field_{key}"
        payload[key] = _normalize_value(value)

    logger.info(event, extra=payload)
