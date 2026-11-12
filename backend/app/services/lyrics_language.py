"""Which language a song is sung in, for picking the alignment and ASR models."""

import logging
import os
import re
from pathlib import Path
from time import perf_counter
from typing import TypedDict

from app.services.gpu_idle_cleanup import begin_gpu_activity, end_gpu_activity
from app.services.gpu_memory import is_cuda_out_of_memory
from app.services.lyrics_alignment import _is_cuda_device, _resolve_alignment_device
from app.services.lyrics_timing import log_lyrics_event

logger = logging.getLogger(__name__)

# Used when a song has no stored language and detection fails or is unsure.
DEFAULT_LANGUAGE = "en"
# A detection from the singing is used for a run only at or above this
# probability. It is never stored: Whisper hears accents, patois and short
# windows of singing as other languages (Muse as Danish at 0.52, reggae as
# Yoruba at 0.74), while real French and Spanish songs can score lower.
MIN_DETECTION_PROBABILITY = 0.5
# A detection from the lyrics text is used, and stored, at or above this.
MIN_LYRICS_PROBABILITY = 0.9
# Detection listens to up to this many 30s windows of singing.
_DETECTION_WINDOWS = 3
# Less text than this (letters, after LRC timestamps and tags are removed) is
# too little to judge a language by.
_MIN_LYRICS_LETTERS = 200
_LRC_TAG = re.compile(r"\[[^\]]*\]")
# langdetect's codes that differ from Whisper's.
_LANGDETECT_TO_WHISPER = {"zh-cn": "zh", "zh-tw": "zh"}


class DetectedLanguage(TypedDict):
    language: str
    probability: float


def whisper_language_codes() -> list[str]:
    """Every language Whisper can detect and transcribe, as codes ("en", "fr")."""
    from faster_whisper.tokenizer import _LANGUAGE_CODES

    return list(_LANGUAGE_CODES)


def normalize_language(value: str | None) -> str | None:
    """A stored language code from user input; None for blank (detect it instead).

    Raises ValueError for a code Whisper doesn't know.
    """
    code = (value or "").strip().lower()
    if not code:
        return None
    if code not in whisper_language_codes():
        raise ValueError(f"Unknown language code: {value}")
    return code


def supports_word_alignment(language: str) -> bool:
    """Whether WhisperX can produce word timings we can store for this language.

    Japanese and Chinese have alignment models, but WhisperX aligns them per
    character, and stored words are checked against the lyrics split on spaces.
    """
    import whisperx.alignment as alignment

    if language in alignment.LANGUAGES_WITHOUT_SPACES:
        return False
    return (
        language in alignment.DEFAULT_ALIGN_MODELS_TORCH
        or language in alignment.DEFAULT_ALIGN_MODELS_HF
    )


def detect_lyrics_language(lyrics: str | None) -> DetectedLanguage | None:
    """Detect the language lyrics are written in, from their text.

    Plain or LRC text; timestamps and [Chorus]-style tags are ignored. None when
    there is too little text or the language isn't one Whisper knows.
    """
    from langdetect import DetectorFactory, LangDetectException, detect_langs

    text = _LRC_TAG.sub(" ", lyrics or "")
    if sum(ch.isalpha() for ch in text) < _MIN_LYRICS_LETTERS:
        return None
    # langdetect samples at random; a fixed seed gives the same answer every run.
    DetectorFactory.seed = 0
    try:
        best = detect_langs(text)[0]
    except LangDetectException:
        return None
    language = _LANGDETECT_TO_WHISPER.get(best.lang, best.lang)
    if language not in whisper_language_codes():
        return None
    return {"language": language, "probability": round(float(best.prob), 3)}


def detect_vocals_language(
    song_id: str, vocals_path: Path, device: str | None = None
) -> DetectedLanguage | None:
    """Detect the sung language with Whisper, skipping the silent parts of the vocals stem."""
    from faster_whisper import WhisperModel, decode_audio

    from app.services.lyrics_transcription import _configure_hf_cache_environment

    _configure_hf_cache_environment(song_id)
    resolved_device = _resolve_alignment_device(device)
    is_cuda = _is_cuda_device(resolved_device)
    model_name = (os.getenv("LYRICS_ASR_MODEL") or "small").strip() or "small"
    started_at = perf_counter()

    activity_started = False
    try:
        if is_cuda:
            begin_gpu_activity("lyrics-language-detection")
            activity_started = True
        model = WhisperModel(
            model_name,
            device="cuda" if is_cuda else "cpu",
            compute_type="float16" if is_cuda else "int8",
        )
        audio = decode_audio(str(vocals_path), sampling_rate=16000)
        language, probability, _ = model.detect_language(
            audio,
            vad_filter=True,
            language_detection_segments=_DETECTION_WINDOWS,
        )
    except Exception as exc:
        if is_cuda_out_of_memory(exc):
            raise
        # Includes a stem with no detectable singing at all.
        logger.warning("Language detection failed for song %s", song_id, exc_info=True)
        log_lyrics_event(song_id, "lyrics_language_detection_failed", model=model_name)
        return None
    finally:
        if activity_started:
            end_gpu_activity("lyrics-language-detection")

    probability = round(float(probability), 3)
    log_lyrics_event(
        song_id,
        "lyrics_language_detected",
        language=language,
        probability=probability,
        model=model_name,
        elapsed_ms=round((perf_counter() - started_at) * 1000, 1),
    )
    return {"language": language, "probability": probability}
