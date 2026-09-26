"""Lyrics-alignment Celery tasks."""

import json

from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Optional

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

logger = get_task_logger(__name__)


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
    alignment_payload = {
        **transcription["alignment"],
        "lyrics_source_type": "synced",
        "lyrics_source": f"asr:{asr_provider}",
        "lyrics_attempt": 0,
        "fallback_reason": fallback_reason,
        "asr_provider": asr_provider,
        "asr_model": asr_model,
    }

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if not song:
            return False

        song.plain_lyrics = transcription["plain_lyrics"]
        song.synced_lyrics = formatted_synced_lyrics
        song.word_synced_lyrics = json.dumps(alignment_payload)
        session.commit()

    transcription["synced_lyrics"] = formatted_synced_lyrics
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
    language: str = "en",
) -> dict:
    """Run WhisperX forced alignment against vocals.mp3 and store word-level timings."""
    logger.info("[PIPELINE] align_song_lyrics starting for song %s", song_id)
    from app.config import get_config
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    MIN_SCORE = 0.3
    synced_recovery_modes = ["synced_padded_small", "synced_padded_medium", "synced_stripped_plain"]
    task_started_at = perf_counter()
    alignment_cache: dict[tuple[str, str, str, str], dict | None] = {}
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

    best_result = None
    best_attempt = None
    best_synced_result = None
    best_synced_attempt = None
    align_error_count = 0

    for idx, attempt in enumerate(attempts):
        source_type = attempt["source_type"]
        source_label = attempt["source"]
        alignment_mode = "plain" if source_type == "plain" else "synced_strict"
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
                alignment_cache=alignment_cache,
                alignment_mode=alignment_mode,
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

        if result["mean_score"] >= MIN_SCORE:
            persist_started_at = perf_counter()
            with get_db_session() as session:
                song = SongRepository(session).fetch(song_id)
                if not song:
                    return {"status": "not_found", "song_id": song_id}

                should_persist_plain_lyrics = bool(
                    attempt["persist"] and source_type == "plain" and not song.plain_lyrics
                )
                should_persist_synced_lyrics = bool(
                    attempt["persist"] and source_type == "synced" and not song.synced_lyrics
                )

                song.word_synced_lyrics = json.dumps(
                    {
                        "words": result["words"],
                        "instrumental_intervals": result.get("instrumental_intervals", []),
                        "language": result["language"],
                        "mean_score": result["mean_score"],
                        "word_count": result["word_count"],
                        "line_count": result["line_count"],
                        "aligned_at": result["aligned_at"],
                        "lyrics_source_type": source_type,
                        "lyrics_source": source_label,
                        "lyrics_attempt": idx + 1,
                    }
                )

                if attempt["persist"]:
                    if should_persist_plain_lyrics:
                        song.plain_lyrics = attempt["content"]
                    if should_persist_synced_lyrics:
                        song.synced_lyrics = attempt["content"]

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
            from app.services.lyrics_offset import compute_whisperx_offset_evidence, shift_lrc_timestamps

            MIN_OFFSET_ANCHORS = 6
            MAX_OFFSET_SPREAD_SECONDS = 3.0
            MAX_ABS_OFFSET_SECONDS = 12.0
            MIN_INLIER_RATIO = 0.55
            MIN_INLIER_COUNT = 8

            def _required_cluster_quality(inlier_ratio: float) -> float:
                if inlier_ratio >= 0.75:
                    return 0.18
                if inlier_ratio >= 0.65:
                    return 0.22
                if inlier_ratio >= 0.55:
                    return 0.26
                return 0.30

            offset_candidates: list[dict[str, Any]] = []

            def _offset_candidate_rejection_reason(evidence):
                offset = evidence["offset"]
                spread = evidence["spread"]
                anchor_count = evidence["anchor_count"]
                inlier_count = evidence.get("inlier_count", 0)
                inlier_ratio = evidence.get("inlier_ratio", 0.0)
                cluster_quality = evidence.get("cluster_quality", 0.0)
                if offset is None or spread is None:
                    return "missing_offset_or_spread"
                if anchor_count < MIN_OFFSET_ANCHORS:
                    return "insufficient_anchors"
                if inlier_count < MIN_INLIER_COUNT:
                    return "insufficient_inliers"
                if inlier_ratio < MIN_INLIER_RATIO:
                    return "low_inlier_ratio"
                if cluster_quality < _required_cluster_quality(inlier_ratio):
                    return "low_cluster_quality"
                if spread > MAX_OFFSET_SPREAD_SECONDS:
                    return "spread_too_wide"
                if abs(offset) > MAX_ABS_OFFSET_SECONDS:
                    return "offset_too_large"
                return None

            best_offset_candidate = None
            strict_evidence = compute_whisperx_offset_evidence(best_synced_result, best_synced_attempt["content"])
            strict_reason = _offset_candidate_rejection_reason(strict_evidence)
            offset_candidates.append(
                {
                    "alignment_mode": "synced_strict",
                    "anchor_count": strict_evidence["anchor_count"],
                    "offset": strict_evidence["offset"],
                    "spread": strict_evidence["spread"],
                    "cluster_count": strict_evidence.get("cluster_count"),
                    "inlier_count": strict_evidence.get("inlier_count"),
                    "inlier_ratio": strict_evidence.get("inlier_ratio"),
                    "cluster_quality": strict_evidence.get("cluster_quality"),
                    "outlier_line_count": len(strict_evidence.get("outlier_line_indices", [])),
                    "mean_score": best_synced_result["mean_score"],
                    "reliable": strict_reason is None,
                    "rejection_reason": strict_reason,
                }
            )
            if strict_reason is None:
                best_offset_candidate = {
                    "alignment_mode": "synced_strict",
                    "offset": strict_evidence["offset"],
                    "evidence": strict_evidence,
                    "result": best_synced_result,
                }
            else:
                logger.info(
                    "align_song_lyrics: rejected strict offset candidate for song %s "
                    "(reason=%s, anchors=%s, spread=%s, offset=%s, inlier_ratio=%s, cluster_quality=%s)",
                    song_id,
                    strict_reason,
                    strict_evidence["anchor_count"],
                    strict_evidence["spread"],
                    strict_evidence["offset"],
                    strict_evidence.get("inlier_ratio"),
                    strict_evidence.get("cluster_quality"),
                )

            for recovery_mode in synced_recovery_modes:
                try:
                    recovery_result = run_alignment_attempt(
                        attempt=best_synced_attempt,
                        vocals_path=vocals_path,
                        language=language,
                        alignment_cache=alignment_cache,
                        alignment_mode=recovery_mode,
                    )
                except Exception:
                    align_error_count += 1
                    logger.warning(
                        "align_song_lyrics: recovery mode failed for song %s (source=%s, mode=%s)",
                        song_id,
                        best_synced_attempt["source"],
                        recovery_mode,
                        exc_info=True,
                    )
                    continue

                if not recovery_result:
                    continue

                recovery_evidence = compute_whisperx_offset_evidence(recovery_result, best_synced_attempt["content"])
                recovery_reason = _offset_candidate_rejection_reason(recovery_evidence)
                offset_candidates.append(
                    {
                        "alignment_mode": recovery_mode,
                        "anchor_count": recovery_evidence["anchor_count"],
                        "offset": recovery_evidence["offset"],
                        "spread": recovery_evidence["spread"],
                        "cluster_count": recovery_evidence.get("cluster_count"),
                        "inlier_count": recovery_evidence.get("inlier_count"),
                        "inlier_ratio": recovery_evidence.get("inlier_ratio"),
                        "cluster_quality": recovery_evidence.get("cluster_quality"),
                        "outlier_line_count": len(recovery_evidence.get("outlier_line_indices", [])),
                        "mean_score": recovery_result["mean_score"],
                        "reliable": recovery_reason is None,
                        "rejection_reason": recovery_reason,
                    }
                )

                if recovery_reason is not None:
                    logger.info(
                        "align_song_lyrics: rejected recovery offset candidate for song %s "
                        "(mode=%s, reason=%s, anchors=%s, spread=%s, offset=%s, inlier_ratio=%s, cluster_quality=%s)",
                        song_id,
                        recovery_mode,
                        recovery_reason,
                        recovery_evidence["anchor_count"],
                        recovery_evidence["spread"],
                        recovery_evidence["offset"],
                        recovery_evidence.get("inlier_ratio"),
                        recovery_evidence.get("cluster_quality"),
                    )
                    continue

                current_candidate_score = (
                    -(best_offset_candidate["evidence"]["spread"] or 0.0),
                    best_offset_candidate["evidence"].get("inlier_ratio", 0.0),
                    best_offset_candidate["evidence"].get("cluster_quality", 0.0),
                    best_offset_candidate["evidence"]["anchor_count"],
                    best_offset_candidate["result"]["mean_score"],
                ) if best_offset_candidate is not None else None
                recovery_candidate_score = (
                    -(recovery_evidence["spread"] or 0.0),
                    recovery_evidence.get("inlier_ratio", 0.0),
                    recovery_evidence.get("cluster_quality", 0.0),
                    recovery_evidence["anchor_count"],
                    recovery_result["mean_score"],
                )

                if best_offset_candidate is None or recovery_candidate_score > current_candidate_score:
                    best_offset_candidate = {
                        "alignment_mode": recovery_mode,
                        "offset": recovery_evidence["offset"],
                        "evidence": recovery_evidence,
                        "result": recovery_result,
                    }

            if best_offset_candidate is not None:
                corrected_lrc = shift_lrc_timestamps(best_synced_attempt["content"], -best_offset_candidate["offset"])
                corrected_lrc = _format_synced_lyrics_for_storage(corrected_lrc)
                with get_db_session() as session:
                    song = SongRepository(session).fetch(song_id)
                    if song:
                        song.synced_lyrics = corrected_lrc
                        song.word_synced_lyrics = None
                        session.commit()
                log_lyrics_event(
                    song_id,
                    "lyrics_task_completed",
                    status="offset_corrected",
                    source=best_synced_attempt["source"],
                    source_type=best_synced_attempt["source_type"],
                    alignment_mode=best_offset_candidate["alignment_mode"],
                    anchor_count=best_offset_candidate["evidence"]["anchor_count"],
                    offset_spread=best_offset_candidate["evidence"]["spread"],
                    inlier_count=best_offset_candidate["evidence"].get("inlier_count"),
                    inlier_ratio=best_offset_candidate["evidence"].get("inlier_ratio"),
                    cluster_quality=best_offset_candidate["evidence"].get("cluster_quality"),
                    best_score=best_offset_candidate["result"]["mean_score"],
                    offset=round(best_offset_candidate["offset"], 3),
                    offset_candidates=offset_candidates,
                    attempted=len(attempts),
                    errors=align_error_count,
                    total_elapsed_ms=round((perf_counter() - task_started_at) * 1000, 1),
                    queue_wait_ms=queue_wait_ms,
                )
                _complete_lyrics_alignment_job(
                    song_id,
                    status=JobStatus.COMPLETED,
                    message=(
                        "Synced lyrics corrected by "
                        f"{best_offset_candidate['offset']:+.3f}s using {best_offset_candidate['alignment_mode']}"
                    ),
                )
                return {
                    "status": "offset_corrected",
                    "song_id": song_id,
                    "offset": best_offset_candidate["offset"],
                    "source": best_synced_attempt["source"],
                    "alignment_mode": best_offset_candidate["alignment_mode"],
                    "offset_candidates": offset_candidates,
                    "attempted": len(attempts),
                    "errors": align_error_count,
                }

            best_rejected_candidate = None
            rejected_candidates = [candidate for candidate in offset_candidates if not candidate["reliable"]]
            if rejected_candidates:
                best_rejected_candidate = max(
                    rejected_candidates,
                    key=lambda candidate: (
                        -float(candidate["spread"] or 0.0),
                        candidate.get("inlier_ratio") or 0.0,
                        candidate.get("cluster_quality") or 0.0,
                        candidate["anchor_count"],
                        candidate["mean_score"],
                    ),
                )

            log_lyrics_event(
                song_id,
                "lyrics_offset_candidates_rejected",
                source=best_synced_attempt["source"],
                source_type=best_synced_attempt["source_type"],
                candidate_count=len(offset_candidates),
                rejected_count=len(rejected_candidates),
                best_rejected_candidate=best_rejected_candidate,
                offset_candidates=offset_candidates,
            )

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
            offset_candidates=offset_candidates if best_synced_result and best_synced_attempt else None,
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
            "offset_candidates": offset_candidates if best_synced_result and best_synced_attempt else None,
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
