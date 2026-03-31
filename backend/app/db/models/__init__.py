"""
Database models package exports
"""

# Import all models so they can be imported from the package
from .album import DbAlbum
from .artist import DbArtist
from .base import UNKNOWN_ARTIST, Base
from .host_settings import HostSettings
from .job import DbJob, Job, JobStatus
from .performance import PerformanceHistory
from .queue import KaraokeQueueItem
from .session import KaraokeSession, SessionDevice, SessionPlaybackState
from .song import DbSong
from .song_artist import DbSongArtist
from .user import User

# Make all models available when importing from this package
__all__ = [
    "DbAlbum",
    "DbArtist",
    "Base",
    "UNKNOWN_ARTIST",
    "DbJob",
    "Job",
    "JobStatus",
    "HostSettings",
    "KaraokeSession",
    "KaraokeQueueItem",
    "PerformanceHistory",
    "SessionDevice",
    "SessionPlaybackState",
    "DbSong",
    "DbSongArtist",
    "User",
]
