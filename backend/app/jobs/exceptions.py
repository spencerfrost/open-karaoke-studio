"""Shared exception types for Celery job processing."""

import re

from app.exceptions import ServiceError


class AudioProcessingError(Exception):
    """Raised when an audio processing pipeline step fails."""


# Download failures that say nothing about the video itself — DNS blips,
# dropped connections, YouTube having a bad minute. A later attempt can work.
_TRANSIENT_DOWNLOAD_PATTERN = re.compile(
    r"name resolution|timed out|connection (reset|refused|aborted)"
    r"|temporary failure|network is unreachable|HTTP Error 5\d\d",
    re.IGNORECASE,
)


def is_transient_processing_error(exc: BaseException) -> bool:
    """Whether a processing failure is worth retrying after a wait.

    True for a full GPU (another job or process holding VRAM) and for
    network-level download errors. Anything else — an unavailable or
    age-restricted video, a corrupt file — would fail the same way again.
    """
    from app.services.gpu_memory import is_cuda_out_of_memory

    if is_cuda_out_of_memory(exc):
        return True
    if isinstance(exc, ServiceError):
        return bool(_TRANSIENT_DOWNLOAD_PATTERN.search(str(exc)))
    return False
