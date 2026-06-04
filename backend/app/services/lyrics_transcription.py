"""ASR transcription helpers for generating fallback lyrics from vocals audio."""

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Literal, TypedDict

from app.services.gpu_idle_cleanup import begin_gpu_activity, end_gpu_activity
from app.services.lyrics_alignment import (
    _build_instrumental_intervals,
    _is_cuda_device,
    _resolve_alignment_device,
)
from app.services.lyrics_timing import log_lyrics_event

logger = logging.getLogger(__name__)

ASRProvider = Literal["whisperx", "qwen3"]


class TranscribedLyricsResult(TypedDict):
    plain_lyrics: str
    synced_lyrics: str
    alignment: dict[str, Any]
    asr_provider: ASRProvider
    asr_model: str


def _resolve_hf_cache_dir() -> Path:
    """Return a writable Hugging Face cache directory for ASR model downloads."""
    configured = (os.getenv("LYRICS_HF_CACHE_DIR") or "").strip()
    if configured:
        return Path(configured).expanduser()

    backend_root = Path(__file__).resolve().parents[2]
    return backend_root / ".cache" / "huggingface"


def _configure_hf_cache_environment(song_id: str) -> Path:
    """Ensure Hugging Face cache env vars point to a writable local path."""
    cache_dir = _resolve_hf_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Keep all HF artifacts under one controlled writable root.
    os.environ["HF_HOME"] = str(cache_dir)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(cache_dir / "hub")

    log_lyrics_event(song_id, "lyrics_asr_cache_configured", cache_dir=str(cache_dir))
    return cache_dir


def _song_id_from_vocals_path(vocals_path: Path) -> str:
    return vocals_path.parent.name


def _normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def _resolve_asr_provider(provider: str | None) -> ASRProvider:
    requested = (provider or os.getenv("LYRICS_ASR_PROVIDER") or "whisperx").strip().lower()
    provider_aliases = {
        "whisper": "whisperx",
        "whisperx": "whisperx",
        "qwen": "qwen3",
        "qwen3": "qwen3",
        "qwen3-asr": "qwen3",
    }
    resolved = provider_aliases.get(requested)
    if resolved:
        return resolved

    logger.warning("Unknown ASR provider '%s'; falling back to WhisperX", requested)
    return "whisperx"


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_object_value(obj: Any, keys: list[str]) -> Any:
    for key in keys:
        if isinstance(obj, dict) and key in obj:
            return obj[key]
        if hasattr(obj, key):
            return getattr(obj, key)
    return None


def _clean_segment_text(words: list[str]) -> str:
    raw = " ".join(word for word in words if word)
    return _normalize_text(re.sub(r"\s+([.,!?;:])", r"\1", raw))


def _clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, value))


def _resolve_qwen_confidence(entry: Any) -> float | None:
    raw_confidence = _coerce_float(
        _read_object_value(
            entry,
            ["score", "confidence", "probability", "prob", "conf", "avg_logprob"],
        )
    )
    if raw_confidence is None:
        return None

    # Handle multiple possible formats from ASR backends.
    if 0.0 <= raw_confidence <= 1.0:
        return _clamp_confidence(raw_confidence)
    if 1.0 < raw_confidence <= 100.0:
        return _clamp_confidence(raw_confidence / 100.0)

    # Log-prob style confidence (often negative) mapped to [0,1] without extra deps.
    if raw_confidence < 0.0:
        if raw_confidence <= -6.0:
            return 0.01
        if raw_confidence <= -4.0:
            return 0.05
        if raw_confidence <= -2.0:
            return 0.15
        if raw_confidence <= -1.0:
            return 0.35
        if raw_confidence <= -0.5:
            return 0.55
        return 0.75

    return _clamp_confidence(raw_confidence)


def _estimate_qwen_confidence(*, word_text: str, start: float, end: float, prev_end: float | None) -> float:
    duration = max(0.0, end - start)
    score = 0.2

    if 0.06 <= duration <= 1.2:
        score += 0.45
    if 0.12 <= duration <= 0.7:
        score += 0.2

    if prev_end is not None:
        gap = start - prev_end
        if -0.2 <= gap <= 1.0:
            score += 0.1
        elif gap > 2.0:
            score -= 0.1

    if re.search(r"[A-Za-z0-9]", word_text):
        score += 0.05

    return round(_clamp_confidence(score), 3)


def _build_transcription_result(
    *,
    song_id: str,
    segments: list[dict[str, Any]],
    language: str,
    provider: ASRProvider,
    model_name: str,
    started_at: float,
) -> TranscribedLyricsResult | None:
    plain_lines: list[str] = []
    synced_lines: list[str] = []
    aligned_words: list[dict[str, Any]] = []

    for seg_idx, segment in enumerate(segments):
        text = _normalize_text(str(segment.get("text", "")))
        if not text:
            continue

        plain_lines.append(text)

        segment_start = _coerce_float(segment.get("start"))
        if segment_start is not None:
            synced_lines.append(f"{_format_lrc_timestamp(segment_start)}{text}")

        for word in segment.get("words", []):
            word_text = _normalize_text(str(word.get("word", "")))
            word_start = _coerce_float(word.get("start"))
            word_end = _coerce_float(word.get("end"))
            if not word_text or word_start is None or word_end is None:
                continue
            aligned_words.append(
                {
                    "word": word_text,
                    "start": round(word_start, 3),
                    "end": round(word_end, 3),
                    "score": round(_coerce_float(word.get("score")) or 0.0, 3),
                    "line_index": seg_idx,
                }
            )

    if not plain_lines or not synced_lines:
        logger.warning("%s ASR produced unusable lyric content for %s", provider, song_id)
        log_lyrics_event(song_id, "lyrics_asr_empty", provider=provider)
        return None

    mean_score = round(sum(word["score"] for word in aligned_words) / len(aligned_words), 3) if aligned_words else 0.0
    instrumental_intervals = _build_instrumental_intervals(aligned_words) if aligned_words else []
    aligned_at = datetime.now(timezone.utc).isoformat()

    result: TranscribedLyricsResult = {
        "plain_lyrics": "\n".join(plain_lines),
        "synced_lyrics": "\n".join(synced_lines),
        "alignment": {
            "words": aligned_words,
            "instrumental_intervals": instrumental_intervals,
            "language": language or "unknown",
            "aligned_at": aligned_at,
            "word_count": len(aligned_words),
            "line_count": len(plain_lines),
            "mean_score": mean_score,
            "asr_provider": provider,
            "asr_model": model_name,
        },
        "asr_provider": provider,
        "asr_model": model_name,
    }

    log_lyrics_event(
        song_id,
        "lyrics_asr_finished",
        provider=provider,
        model=model_name,
        elapsed_ms=round((perf_counter() - started_at) * 1000, 1),
        line_count=len(plain_lines),
        word_count=len(aligned_words),
        mean_score=mean_score,
        language=result["alignment"]["language"],
    )
    return result


def _resolve_qwen_language(language: str | None) -> str | None:
    if not language:
        return None

    normalized = language.strip()
    if not normalized:
        return None

    language_map = {
        "en": "English",
        "zh": "Chinese",
        "yue": "Cantonese",
        "ja": "Japanese",
        "ko": "Korean",
        "fr": "French",
        "de": "German",
        "es": "Spanish",
        "it": "Italian",
        "pt": "Portuguese",
    }
    return language_map.get(normalized.lower(), normalized)


def _segment_qwen_timestamps(time_stamps: Any) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    prev_end: float | None = None
    for entry in time_stamps or []:
        word_text = _normalize_text(str(_read_object_value(entry, ["text", "word", "token"]) or ""))
        start = _coerce_float(_read_object_value(entry, ["start_time", "start"]))
        end = _coerce_float(_read_object_value(entry, ["end_time", "end"]))
        if not word_text or start is None or end is None:
            continue
        explicit_confidence = _resolve_qwen_confidence(entry)
        confidence = (
            round(explicit_confidence, 3)
            if explicit_confidence is not None
            else _estimate_qwen_confidence(word_text=word_text, start=start, end=end, prev_end=prev_end)
        )
        words.append({"word": word_text, "start": start, "end": end, "score": confidence})
        prev_end = end

    if not words:
        return []

    segments: list[dict[str, Any]] = []
    current_words: list[dict[str, Any]] = []
    segment_start = words[0]["start"]

    for word in words:
        if current_words:
            previous_word = current_words[-1]
            gap = word["start"] - previous_word["end"]
            previous_text = previous_word["word"]
            should_break = gap > 1.25 or previous_text.endswith((".", "?", "!")) or len(current_words) >= 14
            if should_break:
                segment_end = previous_word["end"]
                segments.append(
                    {
                        "start": segment_start,
                        "end": segment_end,
                        "text": _clean_segment_text([item["word"] for item in current_words]),
                        "words": current_words,
                    }
                )
                current_words = []
                segment_start = word["start"]

        current_words.append(word)

    if current_words:
        segment_end = current_words[-1]["end"]
        segments.append(
            {
                "start": segment_start,
                "end": segment_end,
                "text": _clean_segment_text([item["word"] for item in current_words]),
                "words": current_words,
            }
        )

    return segments


def _transcribe_with_whisperx(
    *,
    song_id: str,
    vocals_path: Path,
    resolved_device: str,
    transcription_language: str | None,
    model_name: str,
    batch_size: int,
    started_at: float,
) -> TranscribedLyricsResult | None:
    import whisperx

    compute_type = "float16" if _is_cuda_device(resolved_device) else "int8"
    activity_started = False
    try:
        if _is_cuda_device(resolved_device):
            begin_gpu_activity(f"lyrics-asr:whisperx:{transcription_language or 'auto'}")
            activity_started = True

        audio = whisperx.load_audio(str(vocals_path))

        model_load_started_at = perf_counter()
        model = whisperx.load_model(
            model_name,
            resolved_device,
            compute_type=compute_type,
            language=transcription_language,
        )
        log_lyrics_event(
            song_id,
            "lyrics_asr_model_loaded",
            provider="whisperx",
            elapsed_ms=round((perf_counter() - model_load_started_at) * 1000, 1),
            language=transcription_language,
            device=resolved_device,
            model=model_name,
        )

        transcribe_started_at = perf_counter()
        transcription = model.transcribe(
            audio,
            batch_size=batch_size,
            language=transcription_language,
            task="transcribe",
        )
        log_lyrics_event(
            song_id,
            "lyrics_asr_transcribe_finished",
            provider="whisperx",
            elapsed_ms=round((perf_counter() - transcribe_started_at) * 1000, 1),
        )
    except Exception:
        logger.error("WhisperX ASR transcription failed for %s", vocals_path, exc_info=True)
        log_lyrics_event(song_id, "lyrics_asr_failed", provider="whisperx")
        return None
    finally:
        if activity_started:
            end_gpu_activity(f"lyrics-asr:whisperx:{transcription_language or 'auto'}")

    raw_segments = transcription.get("segments", []) if isinstance(transcription, dict) else []
    if not raw_segments:
        logger.warning("WhisperX ASR produced no segments for %s", vocals_path)
        log_lyrics_event(song_id, "lyrics_asr_empty", provider="whisperx")
        return None

    aligned_result: dict[str, Any] | None = None
    align_language = (transcription.get("language") if isinstance(transcription, dict) else None) or transcription_language
    align_activity_started = False
    try:
        if _is_cuda_device(resolved_device):
            begin_gpu_activity(f"lyrics-asr-align:whisperx:{align_language or 'auto'}")
            align_activity_started = True
        model_a, metadata = whisperx.load_align_model(language_code=align_language, device=resolved_device)
        aligned_result = whisperx.align(
            raw_segments,
            model_a,
            metadata,
            audio,
            resolved_device,
            return_char_alignments=False,
        )
        log_lyrics_event(
            song_id,
            "lyrics_asr_align_finished",
            provider="whisperx",
            segment_count=len(raw_segments),
            language=align_language,
        )
    except Exception:
        logger.warning("WhisperX ASR alignment failed for %s; using segment timestamps only", vocals_path, exc_info=True)
        log_lyrics_event(song_id, "lyrics_asr_align_failed", provider="whisperx", language=align_language)
    finally:
        if align_activity_started:
            end_gpu_activity(f"lyrics-asr-align:whisperx:{align_language or 'auto'}")

    segments = raw_segments
    if isinstance(aligned_result, dict) and aligned_result.get("segments"):
        segments = aligned_result["segments"]

    return _build_transcription_result(
        song_id=song_id,
        segments=segments,
        language=(align_language or "unknown"),
        provider="whisperx",
        model_name=model_name,
        started_at=started_at,
    )


def _transcribe_with_qwen3(
    *,
    song_id: str,
    vocals_path: Path,
    resolved_device: str,
    transcription_language: str | None,
    model_name: str,
    batch_size: int,
    started_at: float,
) -> TranscribedLyricsResult | None:
    try:
        import torch
        from qwen_asr import Qwen3ASRModel
    except ImportError:
        logger.error("qwen-asr dependency is not installed; cannot run Qwen3 ASR")
        log_lyrics_event(song_id, "lyrics_asr_failed", provider="qwen3", reason="missing_dependency")
        return None

    qwen_language = _resolve_qwen_language(transcription_language)
    aligner_checkpoint = (os.getenv("LYRICS_QWEN_FORCED_ALIGNER") or "Qwen/Qwen3-ForcedAligner-0.6B").strip()
    use_aligner = bool(aligner_checkpoint)
    max_new_tokens = int(os.getenv("LYRICS_QWEN_MAX_NEW_TOKENS", "1024"))

    qwen_dtype = torch.bfloat16 if _is_cuda_device(resolved_device) else torch.float32
    model_kwargs: dict[str, Any] = {
        "dtype": qwen_dtype,
        "device_map": resolved_device if _is_cuda_device(resolved_device) else "cpu",
        "max_inference_batch_size": max(1, int(batch_size)),
        "max_new_tokens": max(128, max_new_tokens),
    }
    if use_aligner:
        model_kwargs["forced_aligner"] = aligner_checkpoint
        model_kwargs["forced_aligner_kwargs"] = {
            "dtype": qwen_dtype,
            "device_map": resolved_device if _is_cuda_device(resolved_device) else "cpu",
        }

    activity_started = False
    try:
        if _is_cuda_device(resolved_device):
            begin_gpu_activity(f"lyrics-asr:qwen3:{transcription_language or 'auto'}")
            activity_started = True

        model_load_started_at = perf_counter()
        model = Qwen3ASRModel.from_pretrained(model_name, **model_kwargs)
        log_lyrics_event(
            song_id,
            "lyrics_asr_model_loaded",
            provider="qwen3",
            elapsed_ms=round((perf_counter() - model_load_started_at) * 1000, 1),
            language=qwen_language,
            device=resolved_device,
            model=model_name,
            forced_aligner=aligner_checkpoint if use_aligner else None,
        )

        transcribe_started_at = perf_counter()
        results = model.transcribe(
            audio=str(vocals_path),
            language=qwen_language,
            return_time_stamps=use_aligner,
        )
        log_lyrics_event(
            song_id,
            "lyrics_asr_transcribe_finished",
            provider="qwen3",
            elapsed_ms=round((perf_counter() - transcribe_started_at) * 1000, 1),
        )
    except Exception:
        logger.error("Qwen3 ASR transcription failed for %s", vocals_path, exc_info=True)
        log_lyrics_event(song_id, "lyrics_asr_failed", provider="qwen3")
        return None
    finally:
        if activity_started:
            end_gpu_activity(f"lyrics-asr:qwen3:{transcription_language or 'auto'}")

    if isinstance(results, list):
        primary_result = results[0] if results else None
    else:
        primary_result = results
    if primary_result is None:
        logger.warning("Qwen3 ASR returned no result for %s", vocals_path)
        log_lyrics_event(song_id, "lyrics_asr_empty", provider="qwen3")
        return None

    text = _normalize_text(str(_read_object_value(primary_result, ["text"]) or ""))
    language = _normalize_text(str(_read_object_value(primary_result, ["language"]) or transcription_language or "unknown"))
    time_stamps = _read_object_value(primary_result, ["time_stamps", "timestamps"])

    segments = _segment_qwen_timestamps(time_stamps)
    if not segments and text:
        segments = [{"start": 0.0, "end": 0.0, "text": text, "words": []}]

    if not segments:
        logger.warning("Qwen3 ASR produced no segments for %s", vocals_path)
        log_lyrics_event(song_id, "lyrics_asr_empty", provider="qwen3")
        return None

    return _build_transcription_result(
        song_id=song_id,
        segments=segments,
        language=language,
        provider="qwen3",
        model_name=model_name,
        started_at=started_at,
    )


def _format_lrc_timestamp(seconds: float) -> str:
    total_centiseconds = max(0, int(round(float(seconds) * 100)))
    minutes, centiseconds = divmod(total_centiseconds, 6000)
    secs, hundredths = divmod(centiseconds, 100)
    return f"[{minutes:02d}:{secs:02d}.{hundredths:02d}]"


def transcribe_lyrics_from_vocals(
    vocals_path: Path,
    language: str = "en",
    device: str = "auto",
    model_name: str | None = None,
    batch_size: int = 16,
    provider: str | None = None,
) -> TranscribedLyricsResult | None:
    """Transcribe vocals and format the result for lyrics storage."""
    song_id = _song_id_from_vocals_path(vocals_path)
    cache_dir = _configure_hf_cache_environment(song_id)
    resolved_provider = _resolve_asr_provider(provider)
    resolved_device = _resolve_alignment_device(device)
    transcription_language = (language or "").strip() or None
    model_env_var = "LYRICS_QWEN_ASR_MODEL" if resolved_provider == "qwen3" else "LYRICS_ASR_MODEL"
    default_model_name = "Qwen/Qwen3-ASR-1.7B" if resolved_provider == "qwen3" else "small"
    resolved_model_name = (model_name or os.getenv(model_env_var) or default_model_name).strip() or default_model_name

    logger.info(
        "Transcribing vocals for song %s with %s ASR (language=%s, device=%s, model=%s, hf_cache=%s)",
        song_id,
        resolved_provider,
        transcription_language,
        resolved_device,
        resolved_model_name,
        cache_dir,
    )
    log_lyrics_event(
        song_id,
        "lyrics_asr_started",
        provider=resolved_provider,
        language=transcription_language,
        device=resolved_device,
        model=resolved_model_name,
    )

    started_at = perf_counter()
    if resolved_provider == "qwen3":
        return _transcribe_with_qwen3(
            song_id=song_id,
            vocals_path=vocals_path,
            resolved_device=resolved_device,
            transcription_language=transcription_language,
            model_name=resolved_model_name,
            batch_size=batch_size,
            started_at=started_at,
        )

    return _transcribe_with_whisperx(
        song_id=song_id,
        vocals_path=vocals_path,
        resolved_device=resolved_device,
        transcription_language=transcription_language,
        model_name=resolved_model_name,
        batch_size=batch_size,
        started_at=started_at,
    )