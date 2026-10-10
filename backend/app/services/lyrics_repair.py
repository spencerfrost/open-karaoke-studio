"""Which songs a library-wide lyrics alignment run should queue, and why."""

import json
import logging
from collections import Counter
from typing import Literal

from sqlalchemy.orm import Session

from app.db.models import DbSong, LyricsReport
from app.services.file_service import FileService
from app.services.lyrics_alignment import recompute_alignment_line_indices

logger = logging.getLogger(__name__)

AlignmentRunMode = Literal["missing", "repair", "all"]
ALIGNMENT_RUN_MODES: tuple[AlignmentRunMode, ...] = ("missing", "repair", "all")

# Why a song needs its lyrics re-run. Order is the order they're reported in.
RepairReason = Literal[
    "no_word_timing",  # synced lyrics, no word timings
    "plain_only",  # plain lyrics only, no word timings
    "plain_timing",  # word timings force-aligned to plain lyrics (made-up windows)
    "words_mismatch",  # word timings that don't read as the stored lyrics, line for line
    "reported",  # an open lyrics report
]
REPAIR_REASONS: tuple[RepairReason, ...] = (
    "no_word_timing",
    "plain_only",
    "plain_timing",
    "words_mismatch",
    "reported",
)


def _word_timing_reasons(song: DbSong) -> list[RepairReason]:
    if not song.word_synced_lyrics:
        if song.synced_lyrics:
            return ["no_word_timing"]
        if song.plain_lyrics:
            return ["plain_only"]
        return []

    try:
        payload = json.loads(song.word_synced_lyrics)
    except (TypeError, ValueError):
        logger.warning("Song %s has unreadable word timings", song.id)
        return ["words_mismatch"]

    if payload.get("lyrics_source_type") == "plain":
        return ["plain_timing"]

    words = payload.get("words") or []
    if not song.synced_lyrics or not words:
        return ["words_mismatch"]
    recomputed = recompute_alignment_line_indices(words, content=song.synced_lyrics)
    if recomputed is None or any(
        old.get("line_index") != new["line_index"]
        for old, new in zip(words, recomputed)
    ):
        return ["words_mismatch"]
    return []


def repair_reasons(song: DbSong, *, reported: bool) -> list[RepairReason]:
    """Why this song's lyrics need a fresh alignment run; empty when they look right."""
    reasons = _word_timing_reasons(song)
    if reported:
        reasons.append("reported")
    return reasons


def select_songs_for_alignment(
    session: Session, mode: AlignmentRunMode
) -> tuple[list[tuple[DbSong, list[RepairReason]]], int]:
    """Songs with vocals that a run in `mode` should queue, each with its repair reasons.

    - `missing`: songs without word timings, whatever lyrics they have.
    - `repair`: songs with any repair reason.
    - `all`: every song with vocals.

    Returns the selected songs and how many songs have vocals.
    """
    file_service = FileService()
    reported_song_ids = {
        row.song_id
        for row in session.query(LyricsReport.song_id)
        .filter(LyricsReport.resolved_at.is_(None))
        .distinct()
    }

    selected: list[tuple[DbSong, list[RepairReason]]] = []
    with_vocals = 0
    for song in session.query(DbSong).order_by(DbSong.date_added).all():
        if not file_service.get_vocals_path(song.id, ".mp3").exists():
            continue
        with_vocals += 1
        reasons = repair_reasons(song, reported=song.id in reported_song_ids)
        if (
            mode == "all"
            or (mode == "missing" and not song.word_synced_lyrics)
            or (mode == "repair" and reasons)
        ):
            selected.append((song, reasons))
    return selected, with_vocals


def count_reasons(selected: list[tuple[DbSong, list[RepairReason]]]) -> dict[str, int]:
    """How many selected songs have each repair reason (a song can have several)."""
    counts = Counter(reason for _, reasons in selected for reason in reasons)
    return {reason: counts.get(reason, 0) for reason in REPAIR_REASONS}
