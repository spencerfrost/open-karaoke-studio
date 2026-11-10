"""Lyrics-alignment Celery tasks."""

import json
from collections.abc import Collection, Mapping
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Any, Optional

from celery.utils.log import get_task_logger

from app.db.models import JobStatus
from app.services.gpu_memory import (
    free_cached_gpu_memory,
    is_cuda_out_of_memory,
    track_gpu_memory,
)
from app.services.lyrics_analysis import analyze_lyrics
from app.services.lyrics_selection import SongData, select_initial_lyrics
from app.services.lyrics_timing import log_lyrics_event

from ._shared import (
    TRANSIENT_RETRY_DELAYS,
    _complete_lyrics_alignment_job,
    _get_lyrics_job_id,
    _update_lyrics_alignment_job,
    job_repository,
)
from .celery_app import celery
from .lyrics_support import build_alignment_attempts_for_song, run_alignment_attempt

if TYPE_CHECKING:
    from app.services.lyrics_offset import LrcOffsetSweep

logger = get_task_logger(__name__)

# An alignment is stored when its mean word score reaches this.
MIN_ALIGNMENT_SCORE = 0.3
# A swept LRC shift is applied only when it beats the unshifted score by this
# much. Measured on known-good songs: a real 1.5–9s offset gains ≥0.058, an
# already-correct LRC gains ≤0.006.
MIN_OFFSET_GAIN = 0.03
# Lyrics are re-timed from an ASR transcript only when at least this share of
# their words matched it. Below it, the text is likely another song or version.
MIN_RETIME_MATCH_RATIO = 0.5


def _format_synced_lyrics_for_storage(content: str, min_confidence: float = 0.3) -> str:
    analysis = analyze_lyrics(content, min_confidence=min_confidence)
    if analysis["candidates"] and analysis["modified_lrc"] != content:
        return analysis["modified_lrc"]
    return content


def _build_alignment_attempts(
    song: SongData,
    include_remote: bool = True,
    max_remote_results: int = 3,
    rejected_keys: Collection[str] = (),
) -> list[dict]:
    return build_alignment_attempts_for_song(
        song,
        include_remote=include_remote,
        max_remote_results=max_remote_results,
        rejected_keys=rejected_keys,
    )


def _format_synced_attempts(attempts: list[dict]) -> list[dict]:
    """Format every synced candidate before it's aligned.

    Formatting inserts blank break lines, which renumbers lines, so a candidate
    has to be aligned in the form it will be stored in. Candidates that turn
    out identical after formatting are aligned once.
    """
    formatted: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for attempt in attempts:
        if attempt["source_type"] == "synced":
            attempt = {
                **attempt,
                "content": _format_synced_lyrics_for_storage(attempt["content"]),
            }
        key = (attempt["source_type"], attempt["content"])
        if key in seen:
            continue
        seen.add(key)
        formatted.append(attempt)
    return formatted


def _fit_words_to_lyrics(
    song_id: str,
    alignment: Mapping[str, Any],
    *,
    content: str,
    source: str,
) -> dict[str, Any] | None:
    """Point every word's line_index into `content`, the exact LRC stored beside it.

    Returns the alignment with line indexes and instrumental intervals derived
    from that text, or None when the words don't read as that text word for
    word. Storing those would highlight different words than the screen shows.
    """
    from app.services.lyrics_alignment import (
        _build_instrumental_intervals,
        recompute_alignment_line_indices,
    )

    words = recompute_alignment_line_indices(alignment["words"], content=content)
    if words is None:
        logger.warning(
            "Lyrics words don't match the lyrics text for song %s (source=%s)",
            song_id,
            source,
        )
        log_lyrics_event(
            song_id,
            "lyrics_words_mismatch",
            source=source,
            word_count=len(alignment["words"]),
        )
        return None

    relabelled = sum(
        1
        for old, new in zip(alignment["words"], words)
        if old["line_index"] != new["line_index"]
    )
    if relabelled:
        log_lyrics_event(
            song_id, "lyrics_words_relabelled", source=source, word_count=relabelled
        )
    return {
        **alignment,
        "words": words,
        "instrumental_intervals": _build_instrumental_intervals(words),
    }


class LyricsChangedDuringRun(Exception):
    """A person saved or reported the song's lyrics while this run was going."""


def _lyrics_run_token(session, song) -> tuple:
    """What a run must still see before it writes: no new pick, no new report.

    A person saving lyrics changes `lyrics_hand_picked_at`; a report adds a
    row or bumps a count. Either means this run's candidates are out of date.
    """
    from app.db.models import LyricsReport

    reports = (
        session.query(LyricsReport.id, LyricsReport.report_count)
        .filter(LyricsReport.song_id == song.id)
        .order_by(LyricsReport.id)
        .all()
    )
    return (
        song.lyrics_hand_picked_at,
        tuple((row.id, row.report_count) for row in reports),
    )


def _fetch_song_for_write(session, song_id: str, run_token: tuple | None):
    """The song, about to be written; raises if its lyrics changed since the run started."""
    from app.repositories.song_repository import SongRepository

    song = SongRepository(session).fetch(song_id)
    if (
        song is not None
        and run_token is not None
        and _lyrics_run_token(session, song) != run_token
    ):
        raise LyricsChangedDuringRun(song_id)
    return song


def _persist_initial_lyrics_candidate(
    song_id: str, candidate: dict[str, Any] | None, run_token: tuple | None = None
) -> tuple[bool, bool]:
    """Persist top remote lyrics candidate without overwriting existing lyric fields."""
    if not candidate:
        return (False, False)

    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    persisted_plain_lyrics = False
    persisted_synced_lyrics = False

    with get_db_session() as session:
        song = _fetch_song_for_write(session, song_id, run_token)
        if not song:
            return (False, False)

        if candidate["source_type"] == "synced" and not song.synced_lyrics:
            formatted_synced_lyrics = _format_synced_lyrics_for_storage(
                candidate["content"]
            )
            candidate["content"] = formatted_synced_lyrics
            song.synced_lyrics = formatted_synced_lyrics
            song.word_synced_lyrics = None
            persisted_synced_lyrics = True
        elif (
            candidate["source_type"] == "plain"
            and not song.plain_lyrics
            and not song.synced_lyrics
        ):
            song.plain_lyrics = candidate["content"]
            persisted_plain_lyrics = True

        if persisted_plain_lyrics or persisted_synced_lyrics:
            session.commit()

    return (persisted_plain_lyrics, persisted_synced_lyrics)


def _build_word_sync_payload(
    result: Mapping[str, Any],
    *,
    source_type: str,
    source: str,
    attempt_index: int,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "words": result["words"],
        "instrumental_intervals": result.get("instrumental_intervals", []),
        "language": result["language"],
        "mean_score": result["mean_score"],
        "word_count": result["word_count"],
        "line_count": result["line_count"],
        "aligned_at": result["aligned_at"],
        "lyrics_source_type": source_type,
        "lyrics_source": source,
        "lyrics_attempt": attempt_index,
        **extra,
    }


def _offset_rejection_reason(sweep: "LrcOffsetSweep") -> str | None:
    if sweep["shift"] == 0.0:
        return "no_shift"
    if sweep["gain"] < MIN_OFFSET_GAIN:
        return "gain_too_small"
    if sweep["score"] < MIN_ALIGNMENT_SCORE:
        return "score_too_low"
    return None


def _apply_offset_correction(
    song_id: str,
    *,
    attempt: dict[str, Any],
    attempt_index: int,
    vocals_path: Path,
    language: str,
    run_token: tuple | None = None,
) -> dict[str, Any] | None:
    """Shift a low-scoring synced LRC to where the vocals actually are.

    Sweeps a range of global shifts (see sweep_lrc_offset), and if one clearly
    beats the LRC as-is, stores the shifted LRC together with its word timings.
    Returns the sweep and final alignment on success, None when the LRC should
    be left alone.
    """
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.lyrics_alignment import align_lyrics_to_vocals
    from app.services.lyrics_offset import shift_lrc_timestamps, sweep_lrc_offset

    sweep_started_at = perf_counter()
    sweep = sweep_lrc_offset(attempt["content"], vocals_path, language=language)
    if sweep is None:
        log_lyrics_event(
            song_id, "lyrics_offset_sweep_failed", source=attempt["source"]
        )
        return None

    rejection_reason = _offset_rejection_reason(sweep)
    log_lyrics_event(
        song_id,
        "lyrics_offset_sweep_finished",
        source=attempt["source"],
        shift=sweep["shift"],
        score=sweep["score"],
        baseline_score=sweep["baseline_score"],
        gain=sweep["gain"],
        accepted=rejection_reason is None,
        rejection_reason=rejection_reason,
        elapsed_ms=round((perf_counter() - sweep_started_at) * 1000, 1),
    )
    if rejection_reason is not None:
        return None

    corrected_lrc = _format_synced_lyrics_for_storage(
        shift_lrc_timestamps(attempt["content"], sweep["shift"])
    )
    # Formatting can insert blank break lines, which renumbers lines — align the
    # exact text being stored so every word's line_index points into it.
    result = align_lyrics_to_vocals(
        corrected_lrc, vocals_path, language=language, alignment_mode="offset_corrected"
    )
    if not result or result["mean_score"] < MIN_ALIGNMENT_SCORE:
        log_lyrics_event(
            song_id,
            "lyrics_offset_realign_rejected",
            source=attempt["source"],
            shift=sweep["shift"],
            mean_score=result["mean_score"] if result else None,
        )
        return None

    fitted = _fit_words_to_lyrics(
        song_id, result, content=corrected_lrc, source=attempt["source"]
    )
    if fitted is None:
        return None
    result = fitted

    with get_db_session() as session:
        song = _fetch_song_for_write(session, song_id, run_token)
        if not song:
            return None
        song.synced_lyrics = corrected_lrc
        song.word_synced_lyrics = json.dumps(
            _build_word_sync_payload(
                result,
                source_type="synced",
                source=attempt["source"],
                attempt_index=attempt_index,
                offset_applied=sweep["shift"],
            )
        )
        session.commit()

    return {"sweep": sweep, "result": result}


def _resolve_song_language(
    song_id: str, *, requested: str | None, stored: str | None, vocals_path: Path
) -> str:
    """The language to align in: the one asked for, the song's, or detected from the vocals.

    A confident detection is stored on the song; an unsure one is used for this
    run only, falling back to English, so the next run tries again.
    """
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.lyrics_language import (
        DEFAULT_LANGUAGE,
        MIN_DETECTION_PROBABILITY,
        detect_vocals_language,
    )

    if requested:
        language, language_source = requested, "requested"
    elif stored:
        language, language_source = stored, "song"
    else:
        _update_lyrics_alignment_job(
            song_id,
            status=JobStatus.PROCESSING,
            progress=15,
            message="Detecting the sung language",
        )
        detected = detect_vocals_language(song_id, vocals_path)
        if detected and detected["probability"] >= MIN_DETECTION_PROBABILITY:
            language, language_source = detected["language"], "detected"
            with get_db_session() as session:
                SongRepository(session).update(song_id, language=language)
        else:
            language, language_source = DEFAULT_LANGUAGE, "default"

    log_lyrics_event(
        song_id,
        "lyrics_language_resolved",
        language=language,
        language_source=language_source,
    )
    return language


def _persist_asr_fallback(
    song_id: str,
    transcription: dict[str, Any],
    fallback_reason: str,
    rejected_keys: Collection[str] = (),
    run_token: tuple | None = None,
) -> bool:
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    formatted_synced_lyrics = _format_synced_lyrics_for_storage(
        transcription["synced_lyrics"]
    )
    asr_provider = str(
        transcription.get("asr_provider")
        or transcription.get("alignment", {}).get("asr_provider")
        or "whisperx"
    )
    asr_model = str(
        transcription.get("asr_model")
        or transcription.get("alignment", {}).get("asr_model")
        or "unknown"
    )
    alignment = transcription["alignment"]
    if alignment["words"]:
        # Formatting inserted break lines; point the words at the formatted text.
        alignment = _fit_words_to_lyrics(
            song_id,
            alignment,
            content=formatted_synced_lyrics,
            source=f"asr:{asr_provider}",
        )
    alignment_payload = (
        {
            **alignment,
            "lyrics_source_type": "synced",
            "lyrics_source": f"asr:{asr_provider}",
            "lyrics_attempt": 0,
            "fallback_reason": fallback_reason,
            "asr_provider": asr_provider,
            "asr_model": asr_model,
        }
        if alignment is not None
        else None
    )

    with get_db_session() as session:
        song = _fetch_song_for_write(session, song_id, run_token)
        if not song:
            return False

        # Plain lyrics already stored (pasted or fetched) are the real words;
        # keep them, unless someone reported them as wrong.
        from app.services.lyrics_retiming import lyrics_words_key

        if (
            not song.plain_lyrics
            or lyrics_words_key(song.plain_lyrics, "plain") in rejected_keys
        ):
            song.plain_lyrics = transcription["plain_lyrics"]
        song.synced_lyrics = formatted_synced_lyrics
        # Without matching words the lyrics still scroll line by line.
        song.word_synced_lyrics = (
            json.dumps(alignment_payload) if alignment_payload else None
        )
        session.commit()

    transcription["synced_lyrics"] = formatted_synced_lyrics
    if alignment_payload:
        transcription["alignment"] = alignment_payload
    return True


def _retime_from_asr(
    song_id: str,
    attempts: list[dict[str, Any]],
    *,
    vocals_path: Path,
    language: str,
    reason: str,
    run_token: tuple | None = None,
) -> dict[str, Any] | None:
    """Time a lyrics candidate's own text from an ASR transcript of the vocals.

    For songs whose lyrics couldn't be aligned as they are: plain lyrics, or
    synced lyrics with bad timestamps. The transcript only supplies the timing;
    the stored words are always the candidate's. Candidates are tried best
    match first. Returns the stored result, or None when ASR is unavailable or
    no candidate matches the singing well enough, leaving the lyrics untimed.
    """
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.lyrics_alignment import align_line_chunks, align_lyrics_to_vocals
    from app.services.lyrics_retiming import (
        lrc_from_aligned_lines,
        lyrics_text_lines,
        plan_retiming,
    )
    from app.services.lyrics_transcription import transcribe_lyrics_from_vocals

    _update_lyrics_alignment_job(
        song_id,
        status=JobStatus.PROCESSING,
        progress=50,
        message="Timing the lyrics from the vocals",
    )
    log_lyrics_event(
        song_id,
        "lyrics_retime_requested",
        reason=reason,
        language=language,
        attempt_count=len(attempts),
    )

    transcription = transcribe_lyrics_from_vocals(
        vocals_path=vocals_path, language=language
    )
    if not transcription:
        log_lyrics_event(song_id, "lyrics_retime_asr_unavailable", reason=reason)
        return None
    asr_source = f"asr:{transcription.get('asr_provider') or 'whisperx'}"
    asr_words = transcription["alignment"]["words"]

    matches = []
    for attempt_index, attempt in enumerate(attempts, 1):
        lines = lyrics_text_lines(attempt["content"], attempt["source_type"])
        plan = plan_retiming(lines, asr_words)
        log_lyrics_event(
            song_id,
            "lyrics_retime_matched",
            source=attempt["source"],
            source_type=attempt["source_type"],
            match_ratio=plan["match_ratio"] if plan else 0.0,
            line_count=len(lines),
            anchor_count=plan["anchor_count"] if plan else 0,
            chunk_count=len(plan["chunks"]) if plan else 0,
        )
        if plan and plan["match_ratio"] >= MIN_RETIME_MATCH_RATIO:
            matches.append((plan, lines, attempt, attempt_index))
    matches.sort(key=lambda match: match[0]["match_ratio"], reverse=True)

    for plan, lines, attempt, attempt_index in matches:
        # ASR only marks the chunks; forced alignment finds each line within
        # them, and the aligned lines become the LRC that is aligned for real.
        chunked = align_line_chunks(
            lines, plan["chunks"], vocals_path, language=language
        )
        retimed_lrc = (
            lrc_from_aligned_lines(lines, chunked["words"]) if chunked else None
        )
        if retimed_lrc is None:
            log_lyrics_event(
                song_id, "lyrics_retime_chunks_failed", source=attempt["source"]
            )
            continue
        lrc = _format_synced_lyrics_for_storage(retimed_lrc)
        result = align_lyrics_to_vocals(
            lrc, vocals_path, language=language, alignment_mode="retimed"
        )
        if not result or result["mean_score"] < MIN_ALIGNMENT_SCORE:
            log_lyrics_event(
                song_id,
                "lyrics_retime_rejected",
                source=attempt["source"],
                mean_score=result["mean_score"] if result else None,
            )
            continue
        fitted = _fit_words_to_lyrics(
            song_id, result, content=lrc, source=attempt["source"]
        )
        if fitted is None:
            continue

        with get_db_session() as session:
            song = _fetch_song_for_write(session, song_id, run_token)
            if not song:
                return None
            song.synced_lyrics = lrc
            if attempt["source_type"] == "plain":
                song.plain_lyrics = attempt["content"]
            song.word_synced_lyrics = json.dumps(
                _build_word_sync_payload(
                    fitted,
                    source_type="synced",
                    source=attempt["source"],
                    attempt_index=attempt_index,
                    retimed_from=attempt["source_type"],
                    retimed_by=asr_source,
                    retime_match_ratio=plan["match_ratio"],
                )
            )
            session.commit()

        return {
            "attempt": attempt,
            "plan": plan,
            "result": fitted,
            "asr_source": asr_source,
        }

    log_lyrics_event(
        song_id, "lyrics_retime_no_fit", reason=reason, matched_candidates=len(matches)
    )
    return None


def _complete_retimed(
    song_id: str,
    retimed: dict[str, Any],
    *,
    reason: str,
    task_started_at: float,
    queue_wait_ms: float | None,
) -> dict[str, Any]:
    attempt = retimed["attempt"]
    log_lyrics_event(
        song_id,
        "lyrics_task_completed",
        status="retimed",
        reason=reason,
        source=attempt["source"],
        source_type=attempt["source_type"],
        retimed_by=retimed["asr_source"],
        match_ratio=retimed["plan"]["match_ratio"],
        mean_score=retimed["result"]["mean_score"],
        total_elapsed_ms=round((perf_counter() - task_started_at) * 1000, 1),
        queue_wait_ms=queue_wait_ms,
    )
    _complete_lyrics_alignment_job(
        song_id,
        status=JobStatus.COMPLETED,
        message=f"Lyrics timed from the vocals ({retimed['result']['word_count']} words)",
    )
    return {
        "status": "retimed",
        "song_id": song_id,
        "source": attempt["source"],
        "reason": reason,
        "retimed_by": retimed["asr_source"],
    }


def _run_asr_fallback(
    song_id: str,
    vocals_path: Path,
    language: str,
    fallback_reason: str,
    rejected_keys: Collection[str] = (),
    run_token: tuple | None = None,
) -> dict | None:
    """Store an ASR transcript as the lyrics.

    Only for songs with no lyrics, or only lyrics someone reported as wrong.
    """
    from app.services.lyrics_transcription import transcribe_lyrics_from_vocals

    _update_lyrics_alignment_job(
        song_id,
        status=JobStatus.PROCESSING,
        progress=50,
        message="Transcribing vocals with ASR fallback",
    )
    log_lyrics_event(
        song_id,
        "lyrics_asr_fallback_requested",
        fallback_reason=fallback_reason,
        language=language,
    )

    transcription = transcribe_lyrics_from_vocals(
        vocals_path=vocals_path, language=language
    )
    if not transcription:
        log_lyrics_event(
            song_id, "lyrics_asr_fallback_unavailable", fallback_reason=fallback_reason
        )
        return None

    asr_provider = str(
        transcription.get("asr_provider")
        or transcription.get("alignment", {}).get("asr_provider")
        or "whisperx"
    )
    asr_model = str(
        transcription.get("asr_model")
        or transcription.get("alignment", {}).get("asr_model")
        or "unknown"
    )

    if not _persist_asr_fallback(
        song_id, transcription, fallback_reason, rejected_keys, run_token
    ):
        return {"status": "not_found", "song_id": song_id}

    log_lyrics_event(
        song_id,
        "lyrics_asr_fallback_persisted",
        fallback_reason=fallback_reason,
        asr_provider=asr_provider,
        asr_model=asr_model,
        line_count=transcription["alignment"]["line_count"],
        word_count=transcription["alignment"]["word_count"],
        mean_score=transcription["alignment"]["mean_score"],
    )
    _complete_lyrics_alignment_job(
        song_id,
        status=JobStatus.COMPLETED,
        message="Lyrics transcribed with ASR fallback",
    )
    return {
        "status": "ok",
        "song_id": song_id,
        "source": f"asr:{asr_provider}",
        "fallback_reason": fallback_reason,
        "asr_provider": asr_provider,
        "asr_model": asr_model,
    }


def _load_song_lyrics_state(song_id: str) -> dict[str, Any] | None:
    """The song's lyrics, and what people said about them, for building candidates.

    `hand_picked_at`: when a person saved the stored lyrics; while set, only
    they are used.
    `rejected_keys`: words keys of lyrics reported as having the wrong words.
    `pending_reports`: (id, kind, report_count) of open reports the app hasn't
    acted on yet; this run acts on them and records what it did.
    """
    from app.db.database import get_db_session
    from app.db.models import LyricsReport
    from app.repositories.lyrics_report_repository import LyricsReportRepository
    from app.repositories.song_repository import SongRepository

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if not song:
            return None
        song_data: SongData = {
            "id": song.id,
            "title": song.title,
            "artist": song.artist,
            "album": song.album,
            "plain_lyrics": song.plain_lyrics,
            "synced_lyrics": song.synced_lyrics,
            "word_synced_lyrics": song.word_synced_lyrics,
        }
        return {
            "song": song_data,
            "language": song.language,
            "hand_picked_at": song.lyrics_hand_picked_at,
            "rejected_keys": LyricsReportRepository(session).rejected_keys(song_id),
            "run_token": _lyrics_run_token(session, song),
            "pending_reports": [
                (row.id, row.kind, row.report_count)
                for row in session.query(
                    LyricsReport.id, LyricsReport.kind, LyricsReport.report_count
                )
                .filter(
                    LyricsReport.song_id == song_id,
                    LyricsReport.resolved_at.is_(None),
                    LyricsReport.outcome.is_(None),
                )
                .order_by(LyricsReport.id)
                .all()
            ],
        }


@celery.task(name="prefetch_song_lyrics")
def prefetch_song_lyrics(
    song_id: str,
    include_remote: bool = True,
    source: Optional[str] = None,
) -> dict:
    """Fetch and persist top plain/synced lyrics candidate before alignment starts."""
    logger.info("[PIPELINE] prefetch_song_lyrics starting for song %s", song_id)

    if source not in {None, "plain", "synced"}:
        logger.warning(
            "prefetch_song_lyrics: invalid source %s for song %s", source, song_id
        )
        return {"status": "invalid_source", "song_id": song_id, "source": source}

    started_at = perf_counter()
    log_lyrics_event(
        song_id,
        "lyrics_prefetch_started",
        include_remote=include_remote,
        requested_source=source,
    )

    state = _load_song_lyrics_state(song_id)
    if state is None:
        log_lyrics_event(song_id, "lyrics_prefetch_song_missing")
        return {"status": "not_found", "song_id": song_id}
    # Lyrics a person saved are never replaced by a fetched copy.
    if state["hand_picked_at"] is not None:
        include_remote = False

    attempts = _build_alignment_attempts(
        state["song"],
        include_remote=include_remote,
        rejected_keys=state["rejected_keys"],
    )
    if source in {"plain", "synced"}:
        attempts = [attempt for attempt in attempts if attempt["source_type"] == source]

    initial_lyrics_attempt = select_initial_lyrics(attempts)
    if not initial_lyrics_attempt:
        log_lyrics_event(
            song_id,
            "lyrics_prefetch_finished",
            status="no_candidate",
            attempt_count=len(attempts),
            elapsed_ms=round((perf_counter() - started_at) * 1000, 1),
            include_remote=include_remote,
            requested_source=source,
        )
        return {
            "status": "no_candidate",
            "song_id": song_id,
            "attempt_count": len(attempts),
        }

    persisted_plain_lyrics, persisted_synced_lyrics = _persist_initial_lyrics_candidate(
        song_id, initial_lyrics_attempt, state["run_token"]
    )

    status = (
        "persisted"
        if (persisted_plain_lyrics or persisted_synced_lyrics)
        else "no_change"
    )
    log_lyrics_event(
        song_id,
        "lyrics_prefetch_finished",
        status=status,
        attempt_count=len(attempts),
        source=initial_lyrics_attempt["source"],
        source_type=initial_lyrics_attempt["source_type"],
        persisted_plain_lyrics=persisted_plain_lyrics,
        persisted_synced_lyrics=persisted_synced_lyrics,
        elapsed_ms=round((perf_counter() - started_at) * 1000, 1),
        include_remote=include_remote,
        requested_source=source,
    )
    return {
        "status": status,
        "song_id": song_id,
        "attempt_count": len(attempts),
        "source": initial_lyrics_attempt["source"],
        "source_type": initial_lyrics_attempt["source_type"],
        "persisted_plain_lyrics": persisted_plain_lyrics,
        "persisted_synced_lyrics": persisted_synced_lyrics,
    }


def _retry_when_gpu_frees_up(task, song_id: str, exc: BaseException) -> dict:
    """The GPU was full: park the job and retry later, or give up after the last wait.

    Raises celery's Retry while retries remain. The song keeps whatever lyrics
    it already has either way.
    """
    retries = task.request.retries
    free_cached_gpu_memory()
    if retries >= task.max_retries:
        logger.error(
            "align_song_lyrics: GPU still full for song %s after %s attempts",
            song_id,
            retries + 1,
        )
        log_lyrics_event(song_id, "lyrics_gpu_full", attempt=retries + 1, gave_up=True)
        _complete_lyrics_alignment_job(
            song_id,
            status=JobStatus.FAILED,
            message="Lyrics timing failed: the GPU stayed full",
            error=str(exc),
        )
        return {"status": "gpu_full", "song_id": song_id}

    delay = TRANSIENT_RETRY_DELAYS[min(retries, len(TRANSIENT_RETRY_DELAYS) - 1)]
    logger.warning(
        "align_song_lyrics: GPU full for song %s, retry %s/%s in %ss: %s",
        song_id,
        retries + 1,
        task.max_retries,
        delay,
        exc,
    )
    log_lyrics_event(
        song_id, "lyrics_gpu_full", attempt=retries + 1, retry_in_seconds=delay
    )
    _update_lyrics_alignment_job(
        song_id,
        status=JobStatus.PENDING,
        progress=0,
        message=f"The server is busy — trying again in {max(1, delay // 60)} min",
    )
    raise task.retry(countdown=delay, exc=exc)


@celery.task(
    bind=True, name="align_song_lyrics", max_retries=len(TRANSIENT_RETRY_DELAYS)
)
def align_song_lyrics(
    self,
    song_id: str,
    include_remote: bool = True,
    source: Optional[str] = None,
    language: Optional[str] = None,
) -> dict:
    """Run WhisperX forced alignment against vocals.mp3 and store word-level timings.

    `language` overrides the song's stored language for this run. If a person
    saves or reports the lyrics while it runs, it stops before its next write
    (or notices once it's done) and queues a fresh run with the new state.
    """
    run: dict[str, Any] = {}
    try:
        with track_gpu_memory("lyrics", song_id):
            result = _align_song_lyrics(
                song_id,
                include_remote=include_remote,
                source=source,
                language=language,
                run=run,
            )
    except LyricsChangedDuringRun:
        log_lyrics_event(song_id, "lyrics_changed_during_run", stopped=True)
        _complete_lyrics_alignment_job(
            song_id,
            status=JobStatus.COMPLETED,
            message="Lyrics changed while aligning; starting again",
        )
        result = {"status": "superseded", "song_id": song_id}
    except Exception as exc:
        if not is_cuda_out_of_memory(exc):
            raise
        return _retry_when_gpu_frees_up(self, song_id, exc)
    else:
        _record_report_outcomes(song_id, result, run.get("pending_reports", []))
        if "token" not in run or not _lyrics_changed_since(song_id, run["token"]):
            return result
        log_lyrics_event(
            song_id,
            "lyrics_changed_during_run",
            stopped=False,
            status=result.get("status"),
        )

    _queue_fresh_run(
        song_id, include_remote=include_remote, source=source, language=language
    )
    return result


def _record_report_outcomes(
    song_id: str, result: Mapping[str, Any], pending_reports: list[tuple]
) -> None:
    """Write what this run did to each report it acted on.

    The lyrics on screen now, against the ones reported: other words were
    "replaced" (or "transcribed" by ASR), the same words newly timed were
    "retimed", and anything else left them "unchanged". A report made again
    during the run is left for the run that report started.
    """
    if not pending_reports:
        return
    from app.db.database import get_db_session
    from app.db.models import LyricsReport
    from app.repositories.song_repository import SongRepository
    from app.services.lyrics_retiming import shown_lyrics_key

    status = result.get("status")
    timed = status in {"ok", "offset_corrected", "retimed"}
    transcribed = status == "ok" and str(result.get("source") or "").startswith("asr:")
    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if song is None:
            return
        shown_key = shown_lyrics_key(song.synced_lyrics, song.plain_lyrics)
        for report_id, kind, report_count in pending_reports:
            report = session.get(LyricsReport, report_id)
            if (
                report is None
                or report.report_count != report_count
                or report.outcome is not None
            ):
                continue
            if transcribed:
                report.outcome = "transcribed"
            elif shown_key != report.words_key:
                report.outcome = "replaced"
            elif timed:
                report.outcome = "retimed"
            else:
                report.outcome = "unchanged"
            log_lyrics_event(
                song_id,
                "lyrics_report_outcome",
                report_id=report_id,
                kind=kind,
                outcome=report.outcome,
            )
        session.commit()


def _lyrics_changed_since(song_id: str, run_token: tuple) -> bool:
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        return song is not None and _lyrics_run_token(session, song) != run_token


def _queue_fresh_run(
    song_id: str,
    *,
    include_remote: bool,
    source: Optional[str],
    language: Optional[str],
) -> None:
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    from .lyrics_dispatch import enqueue_song_alignment

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if song is not None:
            enqueue_song_alignment(
                song, include_remote=include_remote, source=source, language=language
            )


def _align_song_lyrics(
    song_id: str,
    *,
    include_remote: bool,
    source: Optional[str],
    language: Optional[str],
    run: dict[str, Any],
) -> dict:
    logger.info("[PIPELINE] align_song_lyrics starting for song %s", song_id)
    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    task_started_at = perf_counter()
    lyrics_job = job_repository.get_by_id(_get_lyrics_job_id(song_id))
    queue_wait_ms = None
    if lyrics_job and lyrics_job.created_at:
        now = (
            datetime.now(lyrics_job.created_at.tzinfo)
            if lyrics_job.created_at.tzinfo
            else datetime.now()
        )
        queue_wait_ms = round((now - lyrics_job.created_at).total_seconds() * 1000, 1)
    log_lyrics_event(
        song_id,
        "lyrics_task_started",
        lyrics_job_id=_get_lyrics_job_id(song_id),
        queue_wait_ms=queue_wait_ms,
        task_started_at=datetime.now(),
    )

    config = get_config()
    vocals_path = Path(config.BASE_LIBRARY_DIR) / song_id / "vocals.mp3"

    _update_lyrics_alignment_job(
        song_id,
        status=JobStatus.PROCESSING,
        progress=10,
        message=(
            "Fetching lyrics candidates"
            if include_remote
            else "Loading stored lyrics candidates"
        ),
    )

    if source not in {None, "plain", "synced"}:
        logger.warning(
            "align_song_lyrics: invalid source %s for song %s", source, song_id
        )
        _complete_lyrics_alignment_job(
            song_id,
            status=JobStatus.FAILED,
            message="Lyrics alignment failed: invalid source",
            error=f"invalid source: {source}",
        )
        return {"status": "invalid_source", "song_id": song_id, "source": source}

    if not vocals_path.exists():
        logger.warning("align_song_lyrics: vocals.mp3 not found for song %s", song_id)
        log_lyrics_event(song_id, "lyrics_vocals_missing", vocals_path=vocals_path)
        _complete_lyrics_alignment_job(
            song_id,
            status=JobStatus.COMPLETED,
            message="Lyrics alignment skipped: vocals not ready",
        )
        return {"status": "no_audio", "song_id": song_id}

    state = _load_song_lyrics_state(song_id)
    if state is None:
        logger.warning("align_song_lyrics: song %s not found", song_id)
        log_lyrics_event(song_id, "lyrics_song_missing")
        _complete_lyrics_alignment_job(
            song_id,
            status=JobStatus.FAILED,
            message="Lyrics alignment failed: song not found",
            error="song not found",
        )
        return {"status": "not_found", "song_id": song_id}
    song_data: SongData = state["song"]
    stored_language = state["language"]
    rejected_keys = state["rejected_keys"]
    run_token = state["run_token"]
    run["token"] = run_token
    run["pending_reports"] = state["pending_reports"]
    # Lyrics a person saved are only timed, never replaced by a fetched copy.
    if state["hand_picked_at"] is not None:
        include_remote = False
    # Someone said the words are right but out of sync: keep them, re-time them.
    pending_kinds = {kind for _id, kind, _count in state["pending_reports"]}
    retime_only = pending_kinds == {"timing"}
    if retime_only:
        include_remote = False

    language = _resolve_song_language(
        song_id, requested=language, stored=stored_language, vocals_path=vocals_path
    )

    log_lyrics_event(
        song_id,
        "lyrics_source_snapshot",
        has_plain_lyrics=bool(song_data["plain_lyrics"]),
        plain_lyrics_length=len(song_data["plain_lyrics"] or ""),
        has_synced_lyrics=bool(song_data["synced_lyrics"]),
        synced_lyrics_length=len(song_data["synced_lyrics"] or ""),
        has_word_synced_lyrics=bool(song_data["word_synced_lyrics"]),
        artist=song_data["artist"],
        title=song_data["title"],
        include_remote=include_remote,
        requested_source=source,
        language=language,
        hand_picked=state["hand_picked_at"] is not None,
        rejected_count=len(rejected_keys),
    )

    attempts_started_at = perf_counter()
    attempts = _build_alignment_attempts(
        song_data, include_remote=include_remote, rejected_keys=rejected_keys
    )
    if source in {"plain", "synced"}:
        attempts = [attempt for attempt in attempts if attempt["source_type"] == source]
    attempts = _format_synced_attempts(attempts)
    attempts_elapsed_ms = round((perf_counter() - attempts_started_at) * 1000, 1)
    logger.info(
        "align_song_lyrics: built %d attempts for song %s in %.2fs",
        len(attempts),
        song_id,
        attempts_elapsed_ms / 1000,
    )
    log_lyrics_event(
        song_id,
        "lyrics_attempts_built",
        elapsed_ms=attempts_elapsed_ms,
        attempt_count=len(attempts),
        sources=[
            {
                "source": attempt["source"],
                "source_type": attempt["source_type"],
                "persist": attempt["persist"],
            }
            for attempt in attempts
        ],
        include_remote=include_remote,
        requested_source=source,
        language=language,
    )

    initial_lyrics_attempt = select_initial_lyrics(attempts)
    if initial_lyrics_attempt:
        immediate_persist_started_at = perf_counter()
        persisted_plain_lyrics, persisted_synced_lyrics = (
            _persist_initial_lyrics_candidate(
                song_id,
                initial_lyrics_attempt,
                run_token,
            )
        )
        if persisted_plain_lyrics or persisted_synced_lyrics:
            log_lyrics_event(
                song_id,
                "lyrics_initial_persisted",
                source=initial_lyrics_attempt["source"],
                source_type=initial_lyrics_attempt["source_type"],
                persist_elapsed_ms=round(
                    (perf_counter() - immediate_persist_started_at) * 1000, 1
                ),
                persisted_plain_lyrics=persisted_plain_lyrics,
                persisted_synced_lyrics=persisted_synced_lyrics,
                total_elapsed_ms=round((perf_counter() - task_started_at) * 1000, 1),
            )

    _update_lyrics_alignment_job(
        song_id,
        status=JobStatus.PROCESSING,
        progress=35,
        message=(
            "Lyrics fetched, aligning to vocals"
            if include_remote
            else "Stored lyrics loaded, aligning to vocals"
        ),
    )

    if not attempts:
        logger.debug("align_song_lyrics: no lyrics available for song %s", song_id)
        log_lyrics_event(song_id, "lyrics_no_candidates")
        asr_result = _run_asr_fallback(
            song_id, vocals_path, language, "no_candidates", rejected_keys, run_token
        )
        if asr_result:
            return asr_result
        _complete_lyrics_alignment_job(
            song_id,
            status=JobStatus.COMPLETED,
            message="Lyrics alignment finished: no lyrics candidates found",
        )
        return {"status": "no_lyrics", "song_id": song_id}

    from app.services.lyrics_language import supports_word_alignment

    if not supports_word_alignment(language):
        # The lyrics fetched above still scroll line by line.
        log_lyrics_event(
            song_id,
            "lyrics_task_completed",
            status="no_alignment_model",
            language=language,
            total_elapsed_ms=round((perf_counter() - task_started_at) * 1000, 1),
            queue_wait_ms=queue_wait_ms,
        )
        _complete_lyrics_alignment_job(
            song_id,
            status=JobStatus.COMPLETED,
            message=f"Lyrics ready without word timing (no alignment model for '{language}')",
        )
        return {
            "status": "no_alignment_model",
            "song_id": song_id,
            "language": language,
        }

    if retime_only:
        retimed = _retime_from_asr(
            song_id,
            attempts,
            vocals_path=vocals_path,
            language=language,
            reason="timing_reported",
            run_token=run_token,
        )
        if retimed:
            return _complete_retimed(
                song_id,
                retimed,
                reason="timing_reported",
                task_started_at=task_started_at,
                queue_wait_ms=queue_wait_ms,
            )
        log_lyrics_event(
            song_id,
            "lyrics_task_completed",
            status="retime_failed",
            total_elapsed_ms=round((perf_counter() - task_started_at) * 1000, 1),
            queue_wait_ms=queue_wait_ms,
        )
        _complete_lyrics_alignment_job(
            song_id,
            status=JobStatus.COMPLETED,
            message="Couldn't re-time the lyrics to the singing",
        )
        return {"status": "retime_failed", "song_id": song_id}

    # Plain lyrics have no timestamps for WhisperX to search around, so forcing
    # them onto the audio puts words in made-up places. They're timed from an
    # ASR transcript instead, and show untimed if that doesn't work.
    synced_attempts = [
        attempt for attempt in attempts if attempt["source_type"] == "synced"
    ]
    if not synced_attempts:
        log_lyrics_event(song_id, "lyrics_plain_only", attempt_count=len(attempts))
        retimed = _retime_from_asr(
            song_id,
            attempts,
            vocals_path=vocals_path,
            language=language,
            reason="plain_only",
            run_token=run_token,
        )
        if retimed:
            return _complete_retimed(
                song_id,
                retimed,
                reason="plain_only",
                task_started_at=task_started_at,
                queue_wait_ms=queue_wait_ms,
            )
        log_lyrics_event(
            song_id,
            "lyrics_task_completed",
            status="plain_only",
            total_elapsed_ms=round((perf_counter() - task_started_at) * 1000, 1),
            queue_wait_ms=queue_wait_ms,
        )
        _complete_lyrics_alignment_job(
            song_id,
            status=JobStatus.COMPLETED,
            message="Plain lyrics ready without word timing",
        )
        return {"status": "plain_only", "song_id": song_id}

    best_result = None
    best_attempt = None
    best_attempt_index = 0
    align_error_count = 0

    for idx, attempt in enumerate(synced_attempts):
        source_type = attempt["source_type"]
        source_label = attempt["source"]
        attempt_started_at = perf_counter()
        logger.info(
            "align_song_lyrics: attempt %d/%d for song %s (source=%s)",
            idx + 1,
            len(synced_attempts),
            song_id,
            source_label,
        )
        log_lyrics_event(
            song_id,
            "lyrics_attempt_started",
            attempt_index=idx + 1,
            attempt_total=len(synced_attempts),
            source=source_label,
            source_type=source_type,
            content_length=len(attempt["content"]),
        )

        try:
            result = run_alignment_attempt(
                attempt=attempt,
                vocals_path=vocals_path,
                language=language,
            )
        except Exception as exc:
            if is_cuda_out_of_memory(exc):
                raise
            align_error_count += 1
            log_lyrics_event(
                song_id,
                "lyrics_attempt_failed",
                attempt_index=idx + 1,
                source=source_label,
                source_type=source_type,
                elapsed_ms=round((perf_counter() - attempt_started_at) * 1000, 1),
            )
            logger.warning(
                "align_song_lyrics: attempt failed for song %s (source=%s)",
                song_id,
                source_label,
                exc_info=True,
            )
            continue

        if not result:
            log_lyrics_event(
                song_id,
                "lyrics_attempt_empty",
                attempt_index=idx + 1,
                source=source_label,
                source_type=source_type,
                elapsed_ms=round((perf_counter() - attempt_started_at) * 1000, 1),
            )
            logger.info(
                "align_song_lyrics: no words returned for song %s (source=%s)",
                song_id,
                source_label,
            )
            continue

        if not best_result or result["mean_score"] > best_result["mean_score"]:
            best_result = result
            best_attempt = attempt
            best_attempt_index = idx + 1

        log_lyrics_event(
            song_id,
            "lyrics_attempt_finished",
            attempt_index=idx + 1,
            source=source_label,
            source_type=source_type,
            elapsed_ms=round((perf_counter() - attempt_started_at) * 1000, 1),
            word_count=result["word_count"],
            line_count=result["line_count"],
            mean_score=result["mean_score"],
        )

        if result["mean_score"] >= MIN_ALIGNMENT_SCORE:
            fitted = _fit_words_to_lyrics(
                song_id, result, content=attempt["content"], source=source_label
            )
            if fitted is None:
                continue

            persist_started_at = perf_counter()
            with get_db_session() as session:
                song = _fetch_song_for_write(session, song_id, run_token)
                if not song:
                    return {"status": "not_found", "song_id": song_id}

                # The words index into this candidate's text, so its text is
                # stored with them, replacing whatever was there before.
                should_persist_synced_lyrics = song.synced_lyrics != attempt["content"]
                song.synced_lyrics = attempt["content"]
                song.word_synced_lyrics = json.dumps(
                    _build_word_sync_payload(
                        fitted,
                        source_type=source_type,
                        source=source_label,
                        attempt_index=idx + 1,
                    )
                )

                session.commit()

            persist_elapsed_ms = round((perf_counter() - persist_started_at) * 1000, 1)
            log_lyrics_event(
                song_id,
                "lyrics_persisted",
                attempt_index=idx + 1,
                source=source_label,
                source_type=source_type,
                persist_elapsed_ms=persist_elapsed_ms,
                total_elapsed_ms=round((perf_counter() - task_started_at) * 1000, 1),
                word_count=result["word_count"],
                line_count=result["line_count"],
                mean_score=result["mean_score"],
                persisted_synced_lyrics=should_persist_synced_lyrics,
            )

            logger.info(
                "align_song_lyrics: stored %d words (mean_score=%.3f, source=%s) for song %s",
                result["word_count"],
                result["mean_score"],
                source_label,
                song_id,
            )
            _complete_lyrics_alignment_job(
                song_id,
                status=JobStatus.COMPLETED,
                message=(
                    "Lyrics ready"
                    f" ({result['word_count']} words, {perf_counter() - task_started_at:.1f}s)"
                ),
            )
            log_lyrics_event(
                song_id,
                "lyrics_task_completed",
                status="ok",
                source=source_label,
                source_type=source_type,
                total_elapsed_ms=round((perf_counter() - task_started_at) * 1000, 1),
                queue_wait_ms=queue_wait_ms,
            )
            return {"status": "ok", "song_id": song_id, "source": source_label}

    if best_result and best_attempt:
        logger.info(
            "align_song_lyrics: low confidence best=%.3f (source=%s) for song %s",
            best_result["mean_score"],
            best_attempt["source"],
            song_id,
        )

        correction = _apply_offset_correction(
            song_id,
            attempt=best_attempt,
            attempt_index=best_attempt_index,
            vocals_path=vocals_path,
            language=language,
            run_token=run_token,
        )
        if correction:
            sweep = correction["sweep"]
            corrected_result = correction["result"]
            log_lyrics_event(
                song_id,
                "lyrics_task_completed",
                status="offset_corrected",
                source=best_attempt["source"],
                source_type=best_attempt["source_type"],
                offset=sweep["shift"],
                baseline_score=sweep["baseline_score"],
                best_score=corrected_result["mean_score"],
                attempted=len(synced_attempts),
                errors=align_error_count,
                total_elapsed_ms=round((perf_counter() - task_started_at) * 1000, 1),
                queue_wait_ms=queue_wait_ms,
            )
            _complete_lyrics_alignment_job(
                song_id,
                status=JobStatus.COMPLETED,
                message=(
                    f"Synced lyrics shifted {sweep['shift']:+.1f}s to match the vocals"
                    f" ({corrected_result['word_count']} words)"
                ),
            )
            return {
                "status": "offset_corrected",
                "song_id": song_id,
                "offset": sweep["shift"],
                "source": best_attempt["source"],
                "attempted": len(synced_attempts),
                "errors": align_error_count,
            }

        # The song has lyrics, so a transcript never replaces them; it can only time them.
        retimed = _retime_from_asr(
            song_id,
            attempts,
            vocals_path=vocals_path,
            language=language,
            reason="low_confidence",
            run_token=run_token,
        )
        if retimed:
            return _complete_retimed(
                song_id,
                retimed,
                reason="low_confidence",
                task_started_at=task_started_at,
                queue_wait_ms=queue_wait_ms,
            )
        _complete_lyrics_alignment_job(
            song_id,
            status=JobStatus.COMPLETED,
            message=(
                "Lyrics alignment finished with low confidence"
                f" ({best_result['mean_score']:.3f})"
            ),
        )
        log_lyrics_event(
            song_id,
            "lyrics_task_completed",
            status="low_confidence",
            source=best_attempt["source"],
            source_type=best_attempt["source_type"],
            best_score=best_result["mean_score"],
            attempted=len(synced_attempts),
            errors=align_error_count,
            total_elapsed_ms=round((perf_counter() - task_started_at) * 1000, 1),
            queue_wait_ms=queue_wait_ms,
        )
        return {
            "status": "low_confidence",
            "song_id": song_id,
            "best_score": best_result["mean_score"],
            "source": best_attempt["source"],
            "attempted": len(synced_attempts),
            "errors": align_error_count,
        }

    logger.warning("align_song_lyrics: no result produced for song %s", song_id)
    retimed = _retime_from_asr(
        song_id,
        attempts,
        vocals_path=vocals_path,
        language=language,
        reason="no_result",
        run_token=run_token,
    )
    if retimed:
        return _complete_retimed(
            song_id,
            retimed,
            reason="no_result",
            task_started_at=task_started_at,
            queue_wait_ms=queue_wait_ms,
        )
    log_lyrics_event(
        song_id,
        "lyrics_task_completed",
        status="no_result",
        attempted=len(synced_attempts),
        errors=align_error_count,
        total_elapsed_ms=round((perf_counter() - task_started_at) * 1000, 1),
        queue_wait_ms=queue_wait_ms,
    )
    _complete_lyrics_alignment_job(
        song_id,
        status=JobStatus.COMPLETED,
        message="Lyrics alignment finished without a usable result",
    )
    return {
        "status": "no_result",
        "song_id": song_id,
        "attempted": len(synced_attempts),
        "errors": align_error_count,
    }
