"""Time helpers."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Now in UTC, without a zone: what the DateTime columns store and return."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
