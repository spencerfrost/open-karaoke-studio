"""Work on single lyrics lines, leaving the rest of the song alone.

Time the words of one fixed line (align_lyrics_line), and cut stored lines
too long to be one line (split_stored_long_lines, the "Long lyric lines" job).
"""

import json
from typing import Any, Optional, cast

from celery.utils.log import get_task_logger

from app.services.gpu_memory import (
    free_cached_gpu_memory,
    is_cuda_out_of_memory,
    track_gpu_memory,
)
from app.services.lyrics_timing import log_lyrics_event

from ._shared import TRANSIENT_RETRY_DELAYS
from .celery_app import celery

logger = get_task_logger(__name__)


def _set_fix_status(fix_id: Optional[int], status: str) -> None:
    if fix_id is None:
        return
    from app.db.database import get_db_session
    from app.repositories.lyrics_line_fix_repository import LyricsLineFixRepository

    with get_db_session() as session:
        LyricsLineFixRepository(session).set_align_status(fix_id, status)
        session.commit()


def _settle_superseded_fix(fix_id: Optional[int], song_id: str, text: str) -> None:
    """Give a fix whose timing run was superseded its status, so it isn't left "pending".

    A newer edit of the same line (the fix reads something else now) queued
    its own run, which settles it. Otherwise the song's lyrics or word timing
    were replaced under the fix, and whatever replaced them timed the line
    with the rest of the song: "aligned" when the lyrics show the fix and the
    song has word timing, "no_timing" when not.
    """
    if fix_id is None:
        return
    from app.db.database import get_db_session
    from app.repositories.lyrics_line_fix_repository import LyricsLineFixRepository
    from app.repositories.song_repository import SongRepository
    from app.services.lyrics_line_fixes import fix_is_shown, read_word_payload

    with get_db_session() as session:
        repo = LyricsLineFixRepository(session)
        fix = repo.get(fix_id)
        if fix is None or fix.new_text != text:
            return
        song = SongRepository(session).fetch(song_id)
        timed = (
            song is not None
            and read_word_payload(cast(Optional[str], song.word_synced_lyrics))
            is not None
            and fix_is_shown(cast(Optional[str], song.synced_lyrics), fix)
        )
        repo.set_align_status(fix_id, "aligned" if timed else "no_timing")
        session.commit()


def _line_to_time(
    song, line_index: int, text: str, timing_aligned_at: Optional[str]
) -> Optional[dict[str, Any]]:
    """The song's word timing, while it's still the one the edit patched and
    the line still reads `text`. None when there's nothing for this run to do:
    the line was edited again, or the lyrics or the word timing were replaced.
    """
    from app.services.lyrics_analysis import parse_lrc_lines
    from app.services.lyrics_line_fixes import read_word_payload

    if song is None:
        return None
    synced = cast(Optional[str], song.synced_lyrics)
    if not synced:
        return None
    lines = parse_lrc_lines(synced)
    if line_index >= len(lines) or lines[line_index]["text"] != text:
        return None
    payload = read_word_payload(cast(Optional[str], song.word_synced_lyrics))
    if payload is None or payload.get("aligned_at") != timing_aligned_at:
        return None
    return payload


def _align_line(
    song_id: str, line_index: int, text: str, timing_aligned_at: Optional[str]
) -> str:
    """Returns "aligned", "failed", "no_timing" or "superseded"."""
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.file_service import FileService
    from app.services.lyrics_alignment import LineChunk, align_line_chunks
    from app.services.lyrics_analysis import parse_lrc_lines
    from app.services.lyrics_language import supports_word_alignment
    from app.services.lyrics_line_fixes import line_window, replace_line_words

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        payload = _line_to_time(song, line_index, text, timing_aligned_at)
        if payload is None:
            return "superseded"
        assert song is not None
        lrc_lines = parse_lrc_lines(cast(str, song.synced_lyrics))
        language = str(
            cast(Optional[str], song.language) or payload.get("language") or "en"
        )
        duration = cast(Optional[float], song.duration)

    vocals_path = FileService().get_vocals_path(song_id, ".mp3")
    if not vocals_path.exists() or not supports_word_alignment(language):
        return "no_timing"

    start, end = line_window(lrc_lines, payload["words"], line_index, duration)
    log_lyrics_event(
        song_id,
        "lyrics_line_align_started",
        line_index=line_index,
        window_start=round(start, 3),
        window_end=round(end, 3),
    )
    result = align_line_chunks(
        [text],
        [LineChunk(first_line=0, last_line=0, start=start, end=end)],
        vocals_path,
        language=language,
    )
    if result is None or len(result["words"]) != len(text.split()):
        log_lyrics_event(song_id, "lyrics_line_align_failed", line_index=line_index)
        return "failed"

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        # Read again: the line may have been edited, or a whole-song run may
        # have stored new timing, while this one listened. Other lines fixed
        # meanwhile are in `current` and stay as they are.
        current = _line_to_time(song, line_index, text, timing_aligned_at)
        if current is None:
            return "superseded"
        assert song is not None
        new_words = cast(list[dict[str, Any]], result["words"])
        song.word_synced_lyrics = json.dumps(  # type: ignore[assignment]
            replace_line_words(current, line_index, new_words)
        )
        session.commit()

    scores = [w["score"] for w in result["words"]]
    log_lyrics_event(
        song_id,
        "lyrics_line_align_finished",
        line_index=line_index,
        word_count=len(scores),
        mean_score=round(sum(scores) / len(scores), 3) if scores else None,
    )
    return "aligned"


@celery.task(
    bind=True, name="align_lyrics_line", max_retries=len(TRANSIENT_RETRY_DELAYS)
)
def align_lyrics_line(
    self,
    song_id: str,
    line_index: int,
    text: str,
    timing_aligned_at: Optional[str] = None,
    fix_id: Optional[int] = None,
) -> dict:
    """Force-align line `line_index` (reading `text`) inside its own window and patch its words in.

    Runs while the line still reads `text` and the song's word timing is
    still the one the edit patched (`timing_aligned_at`); fixes to other
    lines and offset shifts don't stop it. A line edited again has its own
    run, and replaced lyrics or word timing were timed as a whole song. The
    fix always leaves "pending". A full GPU waits and tries again, like a
    whole-song alignment.
    """
    try:
        with track_gpu_memory("lyrics", song_id):
            status = _align_line(song_id, line_index, text, timing_aligned_at)
    except Exception as exc:
        if not is_cuda_out_of_memory(exc):
            logger.error(
                "align_lyrics_line failed for song %s line %s",
                song_id,
                line_index,
                exc_info=True,
            )
            _set_fix_status(fix_id, "failed")
            raise
        free_cached_gpu_memory()
        retries = self.request.retries
        if retries >= self.max_retries:
            _set_fix_status(fix_id, "failed")
            return {"status": "gpu_full", "song_id": song_id}
        delay = TRANSIENT_RETRY_DELAYS[min(retries, len(TRANSIENT_RETRY_DELAYS) - 1)]
        log_lyrics_event(
            song_id, "lyrics_line_gpu_full", attempt=retries + 1, retry_in_seconds=delay
        )
        raise self.retry(countdown=delay, exc=exc)

    if status == "superseded":
        _settle_superseded_fix(fix_id, song_id, text)
    else:
        _set_fix_status(fix_id, status)
    logger.info("align_lyrics_line: song %s line %s -> %s", song_id, line_index, status)
    return {"status": status, "song_id": song_id, "line_index": line_index}


def split_stored_long_lines(song_id: str) -> str:
    """Cut the song's stored lines that are too long to be one line, from their
    word timing (services/lyrics_line_split).

    Returns "split", "fine" (no line is too long, or none can be cut: its
    words aren't its text) or "no_timing" (no synced lyrics with word timing).
    """
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.lrc_offset_layer import lrc_md5
    from app.services.lyrics_line_fixes import read_word_payload
    from app.services.lyrics_line_split import split_long_lines

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if song is None:
            return "no_timing"
        synced = cast(Optional[str], song.synced_lyrics)
        payload = read_word_payload(cast(Optional[str], song.word_synced_lyrics))
        if not synced or payload is None:
            return "no_timing"
        split = split_long_lines(
            synced, payload, cast(Optional[str], song.plain_lyrics)
        )
        if split is None:
            return "fine"

        # Same words at the same times: an offset sweep of the old text holds
        # for the new one, so it isn't swept again.
        if cast(Optional[str], song.lrc_offset_lrc_md5) == lrc_md5(synced):
            song.lrc_offset_lrc_md5 = lrc_md5(split["synced_lyrics"])  # type: ignore[assignment]
        song.synced_lyrics = split["synced_lyrics"]  # type: ignore[assignment]
        if split["plain_lyrics"] is not None:
            song.plain_lyrics = split["plain_lyrics"]  # type: ignore[assignment]
        song.word_synced_lyrics = json.dumps(split["word_payload"])  # type: ignore[assignment]
        session.commit()

    log_lyrics_event(song_id, "lyrics_long_lines_split", lines=split["lines_split"])
    logger.info(
        "split_stored_long_lines: cut %d long line(s) of song %s",
        split["lines_split"],
        song_id,
    )
    return "split"
