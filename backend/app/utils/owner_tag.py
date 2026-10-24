"""Opaque per-session tag that marks which session a job belongs to.

Job updates go to every client on `/ws/jobs`, which doesn't authenticate anyone, so a
job can't carry its session ID: that is the session's join code. It carries this tag
instead. A device in the session gets the same tag with its session info and compares
the two. The tag is an HMAC of the session ID under the server secret, so it can't be
turned back into the code.
"""

import hashlib
import hmac
from typing import Optional

# Domain separation, so this HMAC never collides with another use of the secret.
_TAG_CONTEXT = b"job-owner:"
_TAG_LENGTH = 16  # hex chars (64 bits) - plenty to tell a handful of sessions apart


def session_owner_tag(session_id: Optional[str]) -> Optional[str]:
    """Return the owner tag for a session, or None when there's no session."""
    if not session_id:
        return None

    from app.config import get_config

    key = str(get_config().SECRET_KEY).encode("utf-8")
    digest = hmac.new(
        key, _TAG_CONTEXT + session_id.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return digest[:_TAG_LENGTH]
