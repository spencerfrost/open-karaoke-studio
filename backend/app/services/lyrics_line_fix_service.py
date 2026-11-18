"""Saving and undoing a fix to one line of a song's lyrics.

The fixed text goes into the stored lyrics straight away, so the TV shows it
on its next read. Only that line's word timing changes: its new words take
over the timing the line had (`carry_line_words`), and `align_lyrics_line`
then times them properly on their own. The line is never left without words,
so a timing run that fails or never happens costs accuracy on that line and
nothing else. The song is not marked hand-picked, and no whole-song alignment
is queued.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional, cast

from sqlalchemy.orm import Session

from app.db.models import DbSong, LyricsLineFix
from app.exceptions import ValidationError
from app.repositories.lyrics_line_fix_repository import LyricsLineFixRepository
from app.services.lyrics_analysis import parse_lrc_lines
from app.services.lyrics_line_fixes import (
    MAX_LINE_LENGTH,
    LineAnchor,
    LineFixSnapshot,
    anchor_for_line,
    carry_line_words,
    clean_line_text,
    find_shown_line,
    fix_is_shown,
    locate_fix,
    read_word_payload,
    replace_line,
    replace_line_words,
)

logger = logging.getLogger(__name__)


class LineFixError(ValidationError):
    """A fix that can't be saved.

    `reason` is "invalid" (the text or the song can't take a fix) or "stale"
    (the line on screen is no longer in the stored lyrics).
    """

    def __init__(self, message: str, reason: Literal["invalid", "stale"]):
        super().__init__(message, error_code=f"line_fix_{reason}")
        self.reason = reason


@dataclass
class LineEdit:
    """What a save or an undo changed, for timing the line again."""

    song_id: str
    line_index: int
    text: str
    # How the line's words stand: "timed" (still the sung words, on their own
    # timing), "carried" (new words on the line's old timing, to be timed
    # again) or "none" (the song has no word timing).
    words: Literal["timed", "carried", "none"]
    # `aligned_at` of the word timing the edit patched: the line is timed
    # again only while the song's word timing is still that one.
    timing_aligned_at: Optional[str] = None

    @property
    def needs_timing(self) -> bool:
        return self.words == "carried"


def _word_timing_aligned_at(song: DbSong) -> Optional[str]:
    payload = read_word_payload(cast(Optional[str], song.word_synced_lyrics))
    aligned_at = payload.get("aligned_at") if payload else None
    return aligned_at if isinstance(aligned_at, str) else None


def _set_line(
    song: DbSong,
    *,
    index: int,
    from_text: str,
    to_text: str,
    anchor: LineAnchor,
    line_start: Optional[float],
) -> Literal["timed", "carried", "none"]:
    """Write `to_text` on synced line `index` (and its plain twin) and on its words.

    Returns how the line's words stand (see `LineEdit.words`).
    """
    synced = cast(str, song.synced_lyrics)
    song.synced_lyrics = replace_line(synced, index, to_text, "synced")  # type: ignore[assignment]

    plain = cast(Optional[str], song.plain_lyrics)
    if plain and plain.strip():
        stand_in = LineFixSnapshot(
            old_text=from_text,
            new_text=to_text,
            line_start=line_start,
            prev_text=anchor.prev_text,
            next_text=anchor.next_text,
            occurrence=anchor.occurrence,
        )
        plain_index = locate_fix(plain, stand_in, "plain")
        if plain_index is not None:
            song.plain_lyrics = replace_line(plain, plain_index, to_text, "plain")  # type: ignore[assignment]

    payload = read_word_payload(cast(Optional[str], song.word_synced_lyrics))
    if payload is None:
        return "none"
    line_words, same_words = carry_line_words(payload, index, to_text)
    song.word_synced_lyrics = json.dumps(  # type: ignore[assignment]
        replace_line_words(payload, index, line_words)
    )
    return "timed" if same_words else "carried"


_STATUS_AFTER_EDIT = {"timed": "aligned", "carried": "pending", "none": "no_timing"}


def save_line_fix(
    db: Session,
    song: DbSong,
    *,
    line_start: float,
    old_text: str,
    new_text: str,
    fixed_by: Optional[str],
    user_id: Optional[int],
) -> tuple[Optional[LyricsLineFix], LineEdit]:
    """Fix the line the screen showed at `line_start` reading `old_text`.

    Fixing a line that already has a fix updates that fix, so the line keeps
    one row with its first text. Typing that first text back removes the fix,
    and None is returned in its place.
    """
    from app.services.lyrics_retiming import shown_lyrics_key

    synced = cast(Optional[str], song.synced_lyrics)
    song_id = cast(str, song.id)
    if not synced or not synced.strip():
        raise LineFixError("This song has no timed lyrics to fix", "invalid")
    if "\n" in new_text or "\r" in new_text:
        raise LineFixError("A fix is one line", "invalid")
    text = clean_line_text(new_text)
    if not text:
        raise LineFixError("Type the words of the line", "invalid")
    if len(text) > MAX_LINE_LENGTH:
        raise LineFixError(f"A line is at most {MAX_LINE_LENGTH} characters", "invalid")

    index = find_shown_line(synced, line_start=line_start, text=old_text)
    if index is None:
        raise LineFixError(
            "The lyrics changed since this line was shown. Try again.", "stale"
        )
    shown_text = parse_lrc_lines(synced)[index]["text"]
    if clean_line_text(shown_text) == text:
        raise LineFixError("That's what the line already says", "invalid")

    repo = LyricsLineFixRepository(db)
    # Anchored: a fix whose own line is gone must not be taken for this
    # line's fix just because this line reads the same words.
    existing = next(
        (
            fix
            for fix in repo.for_song(song_id)
            if locate_fix(synced, fix, anchored=True) == index
        ),
        None,
    )
    first_text = clean_line_text(existing.old_text) if existing else shown_text
    anchor = anchor_for_line(synced, index, reads=[first_text, text])
    words_key = shown_lyrics_key(synced, cast(Optional[str], song.plain_lyrics))
    aligned_at = _word_timing_aligned_at(song)
    now = datetime.now(timezone.utc)

    fix: Optional[LyricsLineFix]
    if existing is not None and text == first_text:
        repo.delete(existing)
        fix = None
    elif existing is not None:
        existing.new_text = text
        existing.line_start = line_start
        existing.prev_text = anchor.prev_text
        existing.next_text = anchor.next_text
        existing.occurrence = anchor.occurrence
        existing.words_key = words_key
        existing.word_timing_aligned_at = aligned_at
        existing.fixed_by = fixed_by
        existing.user_id = user_id
        existing.updated_at = now
        fix = existing
    else:
        fix = repo.add(
            LyricsLineFix(
                song_id=song_id,
                old_text=shown_text,
                new_text=text,
                line_start=line_start,
                prev_text=anchor.prev_text,
                next_text=anchor.next_text,
                occurrence=anchor.occurrence,
                words_key=words_key,
                word_timing_aligned_at=aligned_at,
                fixed_by=fixed_by,
                user_id=user_id,
                created_at=now,
                updated_at=now,
            )
        )

    words = _set_line(
        song,
        index=index,
        from_text=shown_text,
        to_text=text,
        anchor=anchor,
        line_start=line_start,
    )
    if fix is not None:
        fix.align_status = _STATUS_AFTER_EDIT[words]
        fix.aligned_at = None
    db.commit()
    if fix is not None:
        db.refresh(fix)
    logger.info(
        "Lyrics line %s of song %s fixed by %s%s",
        index,
        song_id,
        fixed_by,
        " (fix removed: back to its first text)" if fix is None else "",
    )
    return fix, LineEdit(
        song_id=song_id,
        line_index=index,
        text=text,
        words=words,
        timing_aligned_at=aligned_at,
    )


def undo_line_fix(db: Session, fix: LyricsLineFix) -> Optional[LineEdit]:
    """Remove a fix, putting its line's first text back when the line still shows the fix.

    A lost fix, or one whose line has since been changed by hand, is only
    removed. Returns what changed on screen, or None when nothing did.
    """
    song: Optional[DbSong] = fix.song
    edit: Optional[LineEdit] = None
    synced = cast(Optional[str], song.synced_lyrics) if song else None
    if song is not None and synced and fix_is_shown(synced, fix):
        index = locate_fix(synced, fix)
        assert index is not None  # fix_is_shown found it
        old_text = clean_line_text(fix.old_text)
        anchor = LineAnchor(
            prev_text=fix.prev_text,
            next_text=fix.next_text,
            occurrence=fix.occurrence,
        )
        aligned_at = _word_timing_aligned_at(song)
        words = _set_line(
            song,
            index=index,
            from_text=fix.new_text,
            to_text=old_text,
            anchor=anchor,
            line_start=fix.line_start,
        )
        edit = LineEdit(
            song_id=cast(str, song.id),
            line_index=index,
            text=old_text,
            words=words,
            timing_aligned_at=aligned_at,
        )
    LyricsLineFixRepository(db).delete(fix)
    db.commit()
    logger.info(
        "Lyrics line fix %s on song %s undone (line restored: %s)",
        fix.id,
        fix.song_id,
        edit is not None,
    )
    return edit


def queue_line_timing(edit: LineEdit, *, fix_id: Optional[int]) -> Optional[str]:
    """Time the edited line's words again, when the song has vocals to listen to.

    Returns the Celery task id, or None when nothing was queued: the words
    need no new timing, or there are no vocals (the caller then marks the
    fix "no_timing").
    """
    from app.jobs.celery_app import celery
    from app.jobs.lyrics_dispatch import LYRICS_QUEUE
    from app.services.file_service import FileService

    if (
        not edit.needs_timing
        or not FileService().get_vocals_path(edit.song_id, ".mp3").exists()
    ):
        return None
    task = celery.send_task(
        "align_lyrics_line",
        args=[edit.song_id, edit.line_index, edit.text, edit.timing_aligned_at],
        kwargs={"fix_id": fix_id},
        queue=LYRICS_QUEUE,
    )
    return task.id
