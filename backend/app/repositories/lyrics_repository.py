"""
LyricsRepository provides CRUD operations for managing lyrics records.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models.lyrics import DbLyrics

logger = logging.getLogger(__name__)


class LyricsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_lyrics(self, song_id: str, lyrics_type: str) -> Optional[DbLyrics]:
        """Get the active lyrics of a specific type for a song."""
        return (
            self.db.query(DbLyrics)
            .filter(
                DbLyrics.song_id == song_id,
                DbLyrics.type == lyrics_type,
                DbLyrics.is_active == True,
            )
            .first()
        )

    def get_all_active_lyrics(self, song_id: str) -> List[DbLyrics]:
        """Get all active lyrics for a song (both plain and synced)."""
        return (
            self.db.query(DbLyrics)
            .filter(DbLyrics.song_id == song_id, DbLyrics.is_active == True)
            .all()
        )

    def get_all_lyrics(self, song_id: str) -> List[DbLyrics]:
        """Get all lyrics versions for a song (including inactive)."""
        return (
            self.db.query(DbLyrics)
            .filter(DbLyrics.song_id == song_id)
            .order_by(DbLyrics.type, DbLyrics.created_at.desc())
            .all()
        )

    def save_lyrics(
        self,
        song_id: str,
        lyrics_type: str,
        content: str,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_active: bool = True,
    ) -> DbLyrics:
        """
        Save a new lyrics record. If is_active=True, deactivates other
        lyrics of the same type for this song.
        """
        if is_active:
            self._deactivate_type(song_id, lyrics_type)

        lyrics = DbLyrics(
            song_id=song_id,
            type=lyrics_type,
            content=content,
            source=source,
            metadata_=metadata,
            is_active=is_active,
        )
        self.db.add(lyrics)
        self.db.commit()
        self.db.refresh(lyrics)
        logger.info(
            f"Saved {lyrics_type} lyrics for song {song_id} (source: {source})"
        )
        return lyrics

    def deactivate_type(self, song_id: str, lyrics_type: str) -> None:
        """Deactivate all lyrics of a given type for a song (public interface)."""
        self._deactivate_type(song_id, lyrics_type)
        self.db.commit()

    def set_active(self, lyrics_id: int) -> Optional[DbLyrics]:
        """Set a specific lyrics record as active, deactivating others of same type."""
        lyrics = self.db.query(DbLyrics).filter(DbLyrics.id == lyrics_id).first()
        if not lyrics:
            return None
        self._deactivate_type(lyrics.song_id, lyrics.type)
        lyrics.is_active = True
        self.db.commit()
        self.db.refresh(lyrics)
        return lyrics

    def delete_lyrics(self, lyrics_id: int) -> bool:
        """Delete a specific lyrics record."""
        lyrics = self.db.query(DbLyrics).filter(DbLyrics.id == lyrics_id).first()
        if not lyrics:
            return False
        self.db.delete(lyrics)
        self.db.commit()
        return True

    def _deactivate_type(self, song_id: str, lyrics_type: str) -> None:
        """Deactivate all lyrics of a given type for a song."""
        self.db.query(DbLyrics).filter(
            DbLyrics.song_id == song_id,
            DbLyrics.type == lyrics_type,
            DbLyrics.is_active == True,
        ).update(
            {"is_active": False, "updated_at": datetime.now(timezone.utc)},
            synchronize_session="fetch",
        )
