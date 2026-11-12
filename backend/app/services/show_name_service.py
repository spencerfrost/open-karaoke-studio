"""A song's show name: the musical or film it was written for.

It follows the song's MusicBrainz recording (see
musicbrainz_service._extract_show_name). Every path that looks a recording up
writes through store_detected_show, so the rule lives in one place. A show a
person set, or a person clearing it, is never overwritten.
"""

import logging
from typing import Optional

from app.db.models import DbSong

logger = logging.getLogger(__name__)


def store_detected_show(song: DbSong, show_name: Optional[str]) -> bool:
    """Set the show the song's recording points to, None clearing it.

    Leaves a hand-set show alone. Returns whether the name changed; the
    caller commits.
    """
    if song.show_name_hand_set_at is not None or song.show_name == show_name:
        return False
    logger.info("Show for song %s: %r -> %r", song.id, song.show_name, show_name)
    song.show_name = show_name
    return True
