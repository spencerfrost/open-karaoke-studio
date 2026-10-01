"""Lyrics-alignment Celery tasks."""

import json

from datetime import datetime
from pathlib import Path
from time import perf_counter
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Optional

from app.db.models import JobStatus
from app.services.lyrics_analysis import analyze_lyrics
from app.services.lyrics_selection import SongData, select_initial_lyrics
from app.services.lyrics_timing import log_lyrics_event
from celery.utils.log import get_task_logger

from ._shared import (
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


def _format_synced_lyrics_for_storage(content: str, min_confidence: float = 0.3) -> str:
    analysis = analyze_lyrics(content, min_confidence=min_confidence)
    if analysis["candidates"] and analysis["modified_lrc"] != content:
        return analysis["modified_lrc"]
    return content


def _build_alignment_attempts(song: SongData, include_remote: bool = True, max_remote_results: int = 3) -> list[dict]:
    return build_alignment_attempts_for_song(
        song,
        include_remote=include_remote,
        max_remote_results=max_remote_results,
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
            attempt = {**attempt, "content": _format_synced_lyrics_for_storage(attempt["content"])}
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
    source_type: str,
    content: str,
    source: str,
) -> dict[str, Any] | None:
    """Point every word's line_index into `content`, the exact text stored beside it.

    Returns the alignment with line indexes and instrumental intervals derived
    from that text, or None when the words don't read as that text word for
    word. Storing those would highlight different words than the screen shows.
    """
    from app.services.lyrics_alignment import _build_instrumental_intervals, recompute_alignment_line_indices

    words = recompute_alignment_line_indices(alignment["words"], source_type=source_type, content=content)
    if words is None:
        logger.warning("Lyrics words don't match the lyrics text for song %s (source=%s)", song_id, source)
        log_lyrics_event(
            song_id,
            "lyrics_words_mismatch",
            source=source,
            source_type=source_type,
            word_count=len(alignment["words"]),
        )
        return None

    relabelled = sum(1 for old, new in zip(alignment["words"], words) if old["line_index"] != new["line_index"])
    if relabelled:
        log_lyrics_event(song_id, "lyrics_words_relabelled", source=source, word_count=relabelled)
    return {**alignment, "words": words, "instrumental_intervals": _build_instrumental_intervals(words)}


def _persist_initial_lyrics_candidate(song_id: str, candidate: dict[str, Any] | None) -> tuple[bool, bool]:
    """Persist top remote lyrics candidate without overwriting existing lyric fields."""
    if not candidate:
        return (False, False)

    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    persisted_plain_lyrics = False
    persisted_synced_lyrics = False

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if not song:
            return (False, False)

        if candidate["source_type"] == "synced" and not song.synced_lyrics:
            formatted_synced_lyrics = _format_synced_lyrics_for_storage(candidate["content"])
            candidate["content"] = formatted_synced_lyrics
            song.synced_lyrics = formatted_synced_lyrics
            song.word_synced_lyrics = None
            persisted_synced_lyrics = True
        elif candidate["source_type"] == "plain" and not song.plain_lyrics and not song.synced_lyrics:
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
        log_lyrics_event(song_id, "lyrics_offset_sweep_failed", source=attempt["source"])
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

    corrected_lrc = _format_synced_lyrics_for_storage(shift_lrc_timestamps(attempt["content"], sweep["shift"]))
    # Formatting can insert blank break lines, which renumbers lines — align the
    # exact text being stored so every word's line_index points into it.
    result = align_lyrics_to_vocals(corrected_lrc, vocals_path, language=language, alignment_mode="offset_corrected")
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
        song_id, result, source_type="synced", content=corrected_lrc, source=attempt["source"]
    )
    if fitted is None:
        return None
    result = fitted

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
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


def _resolve_song_language(song_id: str, *, requested: str | None, stored: str | None, vocals_path: Path) -> str:
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
            song_id, status=JobStatus.PROCESSING, progress=15, message="Detecting the sung language"
        )
        detected = detect_vocals_language(song_id, vocals_path)
        if detected and detected["probability"] >= MIN_DETECTION_PROBABILITY:
            language, language_source = detected["language"], "detected"
            with get_db_session() as session:
                SongRepository(session).update(song_id, language=language)
        else:
            language, language_source = DEFAULT_LANGUAGE, "default"

    log_lyrics_event(song_id, "lyrics_language_resolved", language=language, language_source=language_source)
    return language


def _persist_asr_fallback(song_id: str, transcription: dict[str, Any], fallback_reason: str) -> bool:
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    formatted_synced_lyrics = _format_synced_lyrics_for_storage(transcription["synced_lyrics"])
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
            source_type="synced",
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
        song = SongRepository(session).fetch(song_id)
        if not song:
            return False

        song.plain_lyrics = transcription["plain_lyrics"]
        song.synced_lyrics = formatted_synced_lyrics
        # Without matching words the lyrics still scroll line by line.
        song.word_synced_lyrics = json.dumps(alignment_payload) if alignment_payload else None
        session.commit()

    transcription["synced_lyrics"] = formatted_synced_lyrics
    if alignment_payload:
        transcription["alignment"] = alignment_payload
    return True


def _run_asr_fallback(song_id: str, vocals_path: Path, language: str, fallback_reason: str) -> dict | None:
    from app.services.lyrics_transcription import transcribe_lyrics_from_vocals

    _update_lyrics_alignment_job(
        song_id,
        status=JobStatus.PROCESSING,
        progress=50,
        message="Transcribing vocals with ASR fallback",
    )
    log_lyrics_event(song_id, "lyrics_asr_fallback_requested", fallback_reason=fallback_reason, language=language)

    transcription = transcribe_lyrics_from_vocals(vocals_path=vocals_path, language=language)
    if not transcription:
        log_lyrics_event(song_id, "lyrics_asr_fallback_unavailable", fallback_reason=fallback_reason)
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

    if not _persist_asr_fallback(song_id, transcription, fallback_reason):
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


@celery.task(name="prefetch_song_lyrics")
def prefetch_song_lyrics(
    song_id: str,
    include_remote: bool = True,
    source: Optional[str] = None,
) -> dict:
    """Fetch and persist top plain/synced lyrics candidate before alignment starts."""
    logger.info("[PIPELINE] prefetch_song_lyrics starting for song %s", song_id)

    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    if source not in {None, "plain", "synced"}:
        logger.warning("prefetch_song_lyrics: invalid source %s for song %s", source, song_id)
        return {"status": "invalid_source", "song_id": song_id, "source": source}

    started_at = perf_counter()
    log_lyrics_event(song_id, "lyrics_prefetch_started", include_remote=include_remote, requested_source=source)

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if not song:
            log_lyrics_event(song_id, "lyrics_prefetch_song_missing")
            return {"status": "not_found", "song_id": song_id}
        song_data: SongData = {
            "id": song.id,
            "title": song.title,
            "artist": song.artist,
            "album": song.album,
            "plain_lyrics": song.plain_lyrics,
            "synced_lyrics": song.synced_lyrics,
            "word_synced_lyrics": song.word_synced_lyrics,
        }

    attempts = _build_alignment_attempts(song_data, include_remote=include_remote)
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

    persisted_plain_lyrics, persisted_synced_lyrics = _persist_initial_lyrics_candidate(song_id, initial_lyrics_attempt)

    status = "persisted" if (persisted_plain_lyrics or persisted_synced_lyrics) else "no_change"
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


@celery.task(name="align_song_lyrics")
def align_song_lyrics(
    song_id: str,
    include_remote: bool = True,
    source: Optional[str] = None,
    language: Optional[str] = None,
) -> dict:
    """Run WhisperX forced alignment against vocals.mp3 and store word-level timings.

    `language` overrides the song's stored language for this run.
    """
    logger.info("[PIPELINE] align_song_lyrics starting for song %s", song_id)
    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    task_started_at = perf_counter()
    lyrics_job = job_repository.get_by_id(_get_lyrics_job_id(song_id))
    queue_wait_ms = None
    if lyrics_job and lyrics_job.created_at:
        now = datetime.now(lyrics_job.created_at.tzinfo) if lyrics_job.created_at.tzinfo else datetime.now()
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
        message="Fetching lyrics candidates" if include_remote else "Loading stored lyrics candidates",
    )

    if source not in {None, "plain", "synced"}:
        logger.warning("align_song_lyrics: invalid source %s for song %s", source, song_id)
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

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if not song:
            logger.warning("align_song_lyrics: song %s not found", song_id)
            log_lyrics_event(song_id, "lyrics_song_missing")
            _complete_lyrics_alignment_job(
                song_id,
                status=JobStatus.FAILED,
                message="Lyrics alignment failed: song not found",
                error="song not found",
            )
            return {"status": "not_found", "song_id": song_id}
        song_data: SongData = {
            "id": song.id,
            "title": song.title,
            "artist": song.artist,
            "album": song.album,
            "plain_lyrics": song.plain_lyrics,
            "synced_lyrics": song.synced_lyrics,
            "word_synced_lyrics": song.word_synced_lyrics,
        }
        stored_language = song.language

    language = _resolve_song_language(song_id, requested=language, stored=stored_language, vocals_path=vocals_path)

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
    )

    attempts_started_at = perf_counter()
    attempts = _build_alignment_attempts(song_data, include_remote=include_remote)
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
            {"source": attempt["source"], "source_type": attempt["source_type"], "persist": attempt["persist"]}
            for attempt in attempts
        ],
        include_remote=include_remote,
        requested_source=source,
        language=language,
    )

    initial_lyrics_attempt = select_initial_lyrics(attempts)
    if initial_lyrics_attempt:
        immediate_persist_started_at = perf_counter()
        persisted_plain_lyrics, persisted_synced_lyrics = _persist_initial_lyrics_candidate(
            song_id,
            initial_lyrics_attempt,
        )
        if persisted_plain_lyrics or persisted_synced_lyrics:
            log_lyrics_event(
                song_id,
                "lyrics_initial_persisted",
                source=initial_lyrics_attempt["source"],
                source_type=initial_lyrics_attempt["source_type"],
                persist_elapsed_ms=round((perf_counter() - immediate_persist_started_at) * 1000, 1),
                persisted_plain_lyrics=persisted_plain_lyrics,
                persisted_synced_lyrics=persisted_synced_lyrics,
                total_elapsed_ms=round((perf_counter() - task_started_at) * 1000, 1),
            )

    _update_lyrics_alignment_job(
        song_id,
        status=JobStatus.PROCESSING,
        progress=35,
        message="Lyrics fetched, aligning to vocals" if include_remote else "Stored lyrics loaded, aligning to vocals",
    )

    if not attempts:
        logger.debug("align_song_lyrics: no lyrics available for song %s", song_id)
        log_lyrics_event(song_id, "lyrics_no_candidates")
        asr_result = _run_asr_fallback(song_id, vocals_path, language, "no_candidates")
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
        return {"status": "no_alignment_model", "song_id": song_id, "language": language}

    best_result = None
    best_attempt = None
    best_synced_result = None
    best_synced_attempt = None
    best_synced_attempt_index = 0
    align_error_count = 0

    for idx, attempt in enumerate(attempts):
        source_type = attempt["source_type"]
        source_label = attempt["source"]
        alignment_mode = "plain" if source_type == "plain" else "synced"
        attempt_started_at = perf_counter()
        logger.info(
            "align_song_lyrics: attempt %d/%d for song %s (%s, source=%s, mode=%s)",
            idx + 1,
            len(attempts),
            song_id,
            source_type,
            source_label,
            alignment_mode,
        )
        log_lyrics_event(
            song_id,
            "lyrics_attempt_started",
            attempt_index=idx + 1,
            attempt_total=len(attempts),
            source=source_label,
            source_type=source_type,
            alignment_mode=alignment_mode,
            content_length=len(attempt["content"]),
        )

        try:
            result = run_alignment_attempt(
                attempt=attempt,
                vocals_path=vocals_path,
                language=language,
            )
        except Exception:
            align_error_count += 1
            log_lyrics_event(
                song_id,
                "lyrics_attempt_failed",
                attempt_index=idx + 1,
                source=source_label,
                source_type=source_type,
                alignment_mode=alignment_mode,
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
                alignment_mode=alignment_mode,
                elapsed_ms=round((perf_counter() - attempt_started_at) * 1000, 1),
            )
            logger.info("align_song_lyrics: no words returned for song %s (source=%s)", song_id, source_label)
            continue

        if not best_result or result["mean_score"] > best_result["mean_score"]:
            best_result = result
            best_attempt = attempt

        if source_type == "synced" and (
            not best_synced_result or result["mean_score"] > best_synced_result["mean_score"]
        ):
            best_synced_result = result
            best_synced_attempt = attempt
            best_synced_attempt_index = idx + 1

        log_lyrics_event(
            song_id,
            "lyrics_attempt_finished",
            attempt_index=idx + 1,
            source=source_label,
            source_type=source_type,
            alignment_mode=alignment_mode,
            elapsed_ms=round((perf_counter() - attempt_started_at) * 1000, 1),
            word_count=result["word_count"],
            line_count=result["line_count"],
            mean_score=result["mean_score"],
        )

        if result["mean_score"] >= MIN_ALIGNMENT_SCORE:
            fitted = _fit_words_to_lyrics(
                song_id, result, source_type=source_type, content=attempt["content"], source=source_label
            )
            if fitted is None:
                continue

            persist_started_at = perf_counter()
            with get_db_session() as session:
                song = SongRepository(session).fetch(song_id)
                if not song:
                    return {"status": "not_found", "song_id": song_id}

                # The words index into this candidate's text, so its text is
                # stored with them, replacing whatever was there before.
                should_persist_plain_lyrics = source_type == "plain" and song.plain_lyrics != attempt["content"]
                should_persist_synced_lyrics = source_type == "synced" and song.synced_lyrics != attempt["content"]
                if source_type == "plain":
                    song.plain_lyrics = attempt["content"]
                else:
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
                persisted_plain_lyrics=should_persist_plain_lyrics,
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
                message=("Lyrics ready" f" ({result['word_count']} words, {perf_counter() - task_started_at:.1f}s)"),
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

        if best_synced_result and best_synced_attempt:
            correction = _apply_offset_correction(
                song_id,
                attempt=best_synced_attempt,
                attempt_index=best_synced_attempt_index,
                vocals_path=vocals_path,
                language=language,
            )
            if correction:
                sweep = correction["sweep"]
                corrected_result = correction["result"]
                log_lyrics_event(
                    song_id,
                    "lyrics_task_completed",
                    status="offset_corrected",
                    source=best_synced_attempt["source"],
                    source_type=best_synced_attempt["source_type"],
                    offset=sweep["shift"],
                    baseline_score=sweep["baseline_score"],
                    best_score=corrected_result["mean_score"],
                    attempted=len(attempts),
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
                    "source": best_synced_attempt["source"],
                    "attempted": len(attempts),
                    "errors": align_error_count,
                }

        asr_result = _run_asr_fallback(song_id, vocals_path, language, "low_confidence")
        if asr_result:
            return asr_result
        _complete_lyrics_alignment_job(
            song_id,
            status=JobStatus.COMPLETED,
            message=("Lyrics alignment finished with low confidence" f" ({best_result['mean_score']:.3f})"),
        )
        log_lyrics_event(
            song_id,
            "lyrics_task_completed",
            status="low_confidence",
            source=best_attempt["source"],
            source_type=best_attempt["source_type"],
            best_score=best_result["mean_score"],
            attempted=len(attempts),
            errors=align_error_count,
            total_elapsed_ms=round((perf_counter() - task_started_at) * 1000, 1),
            queue_wait_ms=queue_wait_ms,
        )
        return {
            "status": "low_confidence",
            "song_id": song_id,
            "best_score": best_result["mean_score"],
            "source": best_attempt["source"],
            "attempted": len(attempts),
            "errors": align_error_count,
        }

    logger.warning("align_song_lyrics: no result produced for song %s", song_id)
    asr_result = _run_asr_fallback(song_id, vocals_path, language, "no_result")
    if asr_result:
        return asr_result
    log_lyrics_event(
        song_id,
        "lyrics_task_completed",
        status="no_result",
        attempted=len(attempts),
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
        "attempted": len(attempts),
        "errors": align_error_count,
    }
