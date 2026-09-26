import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config.logging import get_structured_logger

logger = get_structured_logger(__name__, {"component": "lyrics_timing"})


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
        payload[key] = _normalize_value(value)

    logger.info(
        event,
        extra={
            "lyrics_event": json.dumps(payload, sort_keys=True),
            **payload,
        },
    )