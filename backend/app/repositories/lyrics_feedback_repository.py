"""
Lyrics feedback repository: answers to "How were the lyrics?" after each song.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.db.models import DbSong, LyricsFeedback, PerformanceHistory

LyricsRating = Literal["spot_on", "a_bit_off", "way_off"]


def word_timing_aligned_at(song: DbSong) -> Optional[str]:
    """When the word timings on screen were made, or None without any."""
    if not song.word_synced_lyrics:
        return None
    try:
        return json.loads(song.word_synced_lyrics).get("aligned_at")
    except (TypeError, ValueError):
        return None


@dataclass
class SongFeedback:
    """Every answer about one song, split by whether it's about what it shows now."""

    song: DbSong
    # Answers about the lyrics and word timings the song shows now, by rating.
    current: dict[str, int] = field(default_factory=dict)
    # Answers about lyrics or timings that have since been replaced.
    earlier: int = 0
    last_answered_at: Optional[datetime] = None
    plays: int = 0


class LyricsFeedbackRepository:
    def __init__(self, db: Session):
        self.db = db

    def answer(
        self,
        *,
        queue_item_id: int,
        song: DbSong,
        rating: LyricsRating,
        words_key: str,
        singer_name: Optional[str],
        answered_by: Optional[str],
        user_id: Optional[int],
        session_id: Optional[str],
    ) -> LyricsFeedback:
        """Record the answer for a queue item, replacing an earlier one."""
        now = datetime.now(timezone.utc)
        feedback = (
            self.db.query(LyricsFeedback)
            .filter_by(queue_item_id=queue_item_id)
            .one_or_none()
        )
        if feedback is None:
            feedback = LyricsFeedback(queue_item_id=queue_item_id, created_at=now)
            self.db.add(feedback)
        feedback.song_id = song.id
        feedback.rating = rating
        feedback.words_key = words_key
        feedback.word_timing_aligned_at = word_timing_aligned_at(song)
        feedback.singer_name = singer_name
        feedback.answered_by = answered_by
        feedback.user_id = user_id
        feedback.session_id = session_id
        feedback.updated_at = now
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def by_song(self) -> list[SongFeedback]:
        """Every song with answers, with how often it has been sung."""
        from app.services.lyrics_retiming import shown_lyrics_key

        rows = (
            self.db.query(LyricsFeedback).options(joinedload(LyricsFeedback.song)).all()
        )
        songs: dict[str, SongFeedback] = {}
        shown: dict[str, tuple[Optional[str], Optional[str]]] = {}
        for row in rows:
            song = row.song
            if song is None:
                continue
            entry = songs.get(song.id)
            if entry is None:
                entry = songs[song.id] = SongFeedback(song=song)
                shown[song.id] = (
                    shown_lyrics_key(song.synced_lyrics, song.plain_lyrics),
                    word_timing_aligned_at(song),
                )
            if (row.words_key, row.word_timing_aligned_at) == shown[song.id]:
                entry.current[row.rating] = entry.current.get(row.rating, 0) + 1
            else:
                entry.earlier += 1
            if (
                entry.last_answered_at is None
                or row.updated_at > entry.last_answered_at
            ):
                entry.last_answered_at = row.updated_at

        if songs:
            plays = (
                self.db.query(PerformanceHistory.song_id, func.count())
                .filter(PerformanceHistory.song_id.in_(songs.keys()))
                .group_by(PerformanceHistory.song_id)
                .all()
            )
            for song_id, count in plays:
                songs[song_id].plays = count

        return list(songs.values())
