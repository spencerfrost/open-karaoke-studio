"""
Lyrics line fix repository: lines of lyrics a person fixed on the stage.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.db.models import LyricsLineFix


class LyricsLineFixRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, fix_id: int) -> Optional[LyricsLineFix]:
        return self.db.get(LyricsLineFix, fix_id)

    def for_song(self, song_id: str) -> list[LyricsLineFix]:
        """A song's fixes, oldest first: the order they are applied in."""
        return (
            self.db.query(LyricsLineFix)
            .filter(LyricsLineFix.song_id == song_id)
            .order_by(LyricsLineFix.id)
            .all()
        )

    def all_with_songs(self) -> list[LyricsLineFix]:
        """Every fix with its song loaded, newest first."""
        return (
            self.db.query(LyricsLineFix)
            .options(joinedload(LyricsLineFix.song))
            .order_by(LyricsLineFix.id.desc())
            .all()
        )

    def add(self, fix: LyricsLineFix) -> LyricsLineFix:
        self.db.add(fix)
        return fix

    def delete(self, fix: LyricsLineFix) -> None:
        self.db.delete(fix)

    def set_align_status(self, fix_id: int, status: str) -> None:
        """Record how timing the fixed line's words went; a deleted fix is ignored."""
        fix = self.get(fix_id)
        if fix is None:
            return
        now = datetime.now(timezone.utc)
        fix.align_status = status
        fix.aligned_at = now if status == "aligned" else None
        fix.updated_at = now
