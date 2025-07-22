"""Songs API Blueprint"""

import logging

from flask import Blueprint

logger = logging.getLogger(__name__)
song_bp = Blueprint("songs", __name__, url_prefix="/api/songs")
from . import (  # pylint: disable=unused-import,wrong-import-position
    artists,
    core,
    files,
    metadata,
    search,
    thumbnails,
)
