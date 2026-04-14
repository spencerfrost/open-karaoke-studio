"""
Lyrics alignment service — forced alignment of known LRC text to vocals audio.

Uses WhisperX's forced alignment pipeline (wav2vec2 phoneme model) to map
existing LRC lines to word-level timestamps. No Whisper ASR transcription is
run; the LRC text is fed directly as input segments, making this fast and
accurate since the correct words are already known.

The wav2vec2 alignment model (~360 MB) is downloaded on first use and cached
by HuggingFace in ~/.cache/huggingface/.
"""

import logging
from pathlib import Path
from typing import TypedDict

import numpy as np

from app.services.gpu_idle_cleanup import begin_gpu_activity, end_gpu_activity
from app.services.audio import load_vocals
from app.services.lyrics_analysis import LrcLine, parse_lrc_lines

logger = logging.getLogger(__name__)


def _is_cuda_device(device: str) -> bool:
    return str(device).lower().startswith("cuda")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class AlignedWord(TypedDict):
    word: str
    start: float  # seconds
    end: float  # seconds
    score: float
    line_index: int  # which LRC line this word belongs to


class AlignmentResult(TypedDict):
    words: list[AlignedWord]
    language: str
    aligned_at: str
    word_count: int
    line_count: int
    mean_score: float  # average confidence across all aligned words


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _lrc_lines_to_segments(lrc_lines: list[LrcLine]) -> list[dict]:
    """
    Convert parsed LRC lines into the segment format expected by whisperx.align().

    Each segment needs "text", "start" (seconds), and "end" (seconds).
    For the end time, use the next line's start timestamp.
    The final line gets a generous 10-second window.
    """
    segments = []
    content_lines = [l for l in lrc_lines if l["text"].strip()]

    for i, line in enumerate(content_lines):
        start_s = line["timestamp"]  # already in seconds from parse_lrc_lines

        if i + 1 < len(content_lines):
            # End at next line's start, clamped to at least 0.5s window
            end_s = max(start_s + 0.5, content_lines[i + 1]["timestamp"])
        else:
            end_s = start_s + 10.0  # generous window for the last line

        segments.append(
            {
                "text": line["text"].strip(),
                "start": start_s,
                "end": end_s,
            }
        )

    return segments


def _build_line_index_map(lrc_lines: list[LrcLine]) -> dict[int, int]:
    """
    Build a mapping from content-line index (0-based among non-blank lines)
    to the original lrc_lines index.
    """
    mapping: dict[int, int] = {}
    content_idx = 0
    for orig_idx, line in enumerate(lrc_lines):
        if line["text"].strip():
            mapping[content_idx] = orig_idx
            content_idx += 1
    return mapping


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def align_lyrics_to_vocals(
    lrc_content: str,
    vocals_path: Path,
    language: str = "en",
    device: str = "cpu",
) -> AlignmentResult | None:
    """
    Align LRC lyrics to vocals audio using WhisperX forced alignment.

    Loads the wav2vec2 phoneme alignment model (downloaded on first use),
    constructs segments from the LRC lines, and runs forced alignment.
    Returns word-level timestamps with their originating line index.

    Returns None if alignment fails or produces no words.
    """
    import whisperx
    from datetime import datetime, timezone

    lrc_lines = parse_lrc_lines(lrc_content)
    if not lrc_lines:
        logger.warning("align_lyrics_to_vocals: no LRC lines found")
        return None

    content_lines = [l for l in lrc_lines if l["text"].strip()]
    if not content_lines:
        logger.warning("align_lyrics_to_vocals: no non-blank LRC lines found")
        return None

    # Load audio
    logger.info("Loading vocals from %s", vocals_path)
    y, sr = load_vocals(vocals_path)
    # WhisperX expects float32 numpy array at 16kHz
    import librosa

    y_16k = librosa.resample(y, orig_sr=sr, target_sr=16000).astype(np.float32)

    # Build segments and line mapping
    segments = _lrc_lines_to_segments(lrc_lines)
    line_index_map = _build_line_index_map(lrc_lines)

    if not segments:
        logger.warning("align_lyrics_to_vocals: no segments constructed")
        return None

    logger.info(
        "Running forced alignment for %d segments (language=%s, device=%s)",
        len(segments),
        language,
        device,
    )

    activity_started = False
    try:
        if _is_cuda_device(device):
            begin_gpu_activity(f"lyrics-alignment:{language}")
            activity_started = True
        model_a, metadata = whisperx.load_align_model(
            language_code=language, device=device
        )
        result = whisperx.align(
            segments,
            model_a,
            metadata,
            y_16k,
            device,
            return_char_alignments=False,
        )
    except Exception as e:
        logger.error("WhisperX alignment failed: %s", e, exc_info=True)
        return None
    finally:
        if activity_started:
            end_gpu_activity(f"lyrics-alignment:{language}")

    # Flatten words from all segments, tagging each with its line index
    aligned_words: list[AlignedWord] = []
    for seg_idx, seg in enumerate(result.get("segments", [])):
        orig_line_idx = line_index_map.get(seg_idx, seg_idx)
        for w in seg.get("words", []):
            # WhisperX may omit start/end if it couldn't align a word
            word_start = w.get("start")
            word_end = w.get("end")
            if word_start is None or word_end is None:
                continue
            aligned_words.append(
                AlignedWord(
                    word=w.get("word", "").strip(),
                    start=round(float(word_start), 3),
                    end=round(float(word_end), 3),
                    score=round(float(w.get("score", 0.0)), 3),
                    line_index=orig_line_idx,
                )
            )

    if not aligned_words:
        logger.warning("align_lyrics_to_vocals: alignment produced no words")
        return None

    logger.info(
        "Alignment complete: %d words across %d lines",
        len(aligned_words),
        len(content_lines),
    )

    mean_score = round(
        sum(w["score"] for w in aligned_words) / len(aligned_words), 3
    )

    return AlignmentResult(
        words=aligned_words,
        language=language,
        aligned_at=datetime.now(timezone.utc).isoformat(),
        word_count=len(aligned_words),
        line_count=len(content_lines),
        mean_score=mean_score,
    )


# ---------------------------------------------------------------------------
# Plain text alignment path
# ---------------------------------------------------------------------------

_SECTION_HEADER_RE = None


def _plain_lines_to_segments(plain_content: str) -> list[dict]:
    """
    Convert plain text lyrics into dummy segments for WhisperX forced alignment.

    Strips blank lines and section headers like [Chorus], [Verse 1], etc.
    Assigns evenly-spaced dummy timestamps (5s apart); WhisperX only uses
    the text and finds the real timing via the acoustic model.
    """
    import re

    header_re = re.compile(r"^\s*\[.*?\]\s*$")
    lines = [
        l.strip()
        for l in plain_content.splitlines()
        if l.strip() and not header_re.match(l)
    ]

    segments = []
    for i, line in enumerate(lines):
        start_s = float(i * 5)
        end_s = start_s + 5.0
        segments.append({"text": line, "start": start_s, "end": end_s})

    return segments


def align_plain_lyrics_to_vocals(
    plain_content: str,
    vocals_path: Path,
    language: str = "en",
    device: str = "cpu",
) -> AlignmentResult | None:
    """
    Align plain text lyrics to vocals using WhisperX forced alignment.

    Uses evenly-spaced dummy timestamps as segment scaffolding — the wav2vec2
    alignment model finds the actual timing. Returns the same AlignmentResult
    as align_lyrics_to_vocals; line_index in AlignedWord maps to the stripped
    line list (section headers excluded).
    """
    import whisperx
    from datetime import datetime, timezone

    segments = _plain_lines_to_segments(plain_content)
    if not segments:
        logger.warning("align_plain_lyrics_to_vocals: no usable lines found")
        return None

    logger.info("Loading vocals from %s", vocals_path)
    y, sr = load_vocals(vocals_path)
    import librosa

    y_16k = librosa.resample(y, orig_sr=sr, target_sr=16000).astype(np.float32)

    logger.info(
        "Running plain-text forced alignment for %d lines (language=%s, device=%s)",
        len(segments),
        language,
        device,
    )

    activity_started = False
    try:
        if _is_cuda_device(device):
            begin_gpu_activity(f"plain-lyrics-alignment:{language}")
            activity_started = True
        model_a, metadata = whisperx.load_align_model(
            language_code=language, device=device
        )
        result = whisperx.align(
            segments,
            model_a,
            metadata,
            y_16k,
            device,
            return_char_alignments=False,
        )
    except Exception as e:
        logger.error("WhisperX plain alignment failed: %s", e, exc_info=True)
        return None
    finally:
        if activity_started:
            end_gpu_activity(f"plain-lyrics-alignment:{language}")

    aligned_words: list[AlignedWord] = []
    for seg_idx, seg in enumerate(result.get("segments", [])):
        for w in seg.get("words", []):
            word_start = w.get("start")
            word_end = w.get("end")
            if word_start is None or word_end is None:
                continue
            aligned_words.append(
                AlignedWord(
                    word=w.get("word", "").strip(),
                    start=round(float(word_start), 3),
                    end=round(float(word_end), 3),
                    score=round(float(w.get("score", 0.0)), 3),
                    line_index=seg_idx,
                )
            )

    if not aligned_words:
        logger.warning("align_plain_lyrics_to_vocals: alignment produced no words")
        return None

    mean_score = round(
        sum(w["score"] for w in aligned_words) / len(aligned_words), 3
    )

    logger.info(
        "Plain alignment complete: %d words, mean_score=%.3f",
        len(aligned_words),
        mean_score,
    )

    return AlignmentResult(
        words=aligned_words,
        language=language,
        aligned_at=datetime.now(timezone.utc).isoformat(),
        word_count=len(aligned_words),
        line_count=len(segments),
        mean_score=mean_score,
    )


# ---------------------------------------------------------------------------
# Batch-friendly: shared model loading
# ---------------------------------------------------------------------------


def load_alignment_model(language: str = "en", device: str = "cpu"):
    """
    Load the WhisperX wav2vec2 alignment model once for reuse across many songs.

    Returns (model_a, metadata) — pass these to align_*_with_model() to avoid
    reloading the ~360 MB model for every song in a batch operation.
    """
    import whisperx

    logger.info("Loading WhisperX alignment model (language=%s, device=%s)", language, device)
    return whisperx.load_align_model(language_code=language, device=device)


def align_lyrics_to_vocals_with_model(
    lrc_content: str,
    vocals_path: Path,
    model_a,
    metadata,
    language: str = "en",
    device: str = "cpu",
) -> AlignmentResult | None:
    """
    Align LRC lyrics using a pre-loaded WhisperX model.

    Identical to align_lyrics_to_vocals() but accepts an already-loaded
    (model_a, metadata) pair so the model is not reloaded per song.
    """
    import whisperx
    from datetime import datetime, timezone

    lrc_lines = parse_lrc_lines(lrc_content)
    if not lrc_lines:
        return None

    content_lines = [l for l in lrc_lines if l["text"].strip()]
    if not content_lines:
        return None

    y, sr = load_vocals(vocals_path)
    import librosa

    y_16k = librosa.resample(y, orig_sr=sr, target_sr=16000).astype(np.float32)

    segments = _lrc_lines_to_segments(lrc_lines)
    line_index_map = _build_line_index_map(lrc_lines)

    if not segments:
        return None

    try:
        result = whisperx.align(
            segments, model_a, metadata, y_16k, device, return_char_alignments=False
        )
    except Exception as e:
        logger.error("WhisperX alignment failed for %s: %s", vocals_path, e, exc_info=True)
        return None

    aligned_words: list[AlignedWord] = []
    for seg_idx, seg in enumerate(result.get("segments", [])):
        orig_line_idx = line_index_map.get(seg_idx, seg_idx)
        for w in seg.get("words", []):
            word_start = w.get("start")
            word_end = w.get("end")
            if word_start is None or word_end is None:
                continue
            aligned_words.append(
                AlignedWord(
                    word=w.get("word", "").strip(),
                    start=round(float(word_start), 3),
                    end=round(float(word_end), 3),
                    score=round(float(w.get("score", 0.0)), 3),
                    line_index=orig_line_idx,
                )
            )

    if not aligned_words:
        return None

    mean_score = round(sum(w["score"] for w in aligned_words) / len(aligned_words), 3)
    return AlignmentResult(
        words=aligned_words,
        language=language,
        aligned_at=datetime.now(timezone.utc).isoformat(),
        word_count=len(aligned_words),
        line_count=len(content_lines),
        mean_score=mean_score,
    )


def align_plain_lyrics_to_vocals_with_model(
    plain_content: str,
    vocals_path: Path,
    model_a,
    metadata,
    language: str = "en",
    device: str = "cpu",
) -> AlignmentResult | None:
    """
    Align plain text lyrics using a pre-loaded WhisperX model.

    Identical to align_plain_lyrics_to_vocals() but accepts an already-loaded
    (model_a, metadata) pair so the model is not reloaded per song.
    """
    import whisperx
    from datetime import datetime, timezone

    segments = _plain_lines_to_segments(plain_content)
    if not segments:
        return None

    y, sr = load_vocals(vocals_path)
    import librosa

    y_16k = librosa.resample(y, orig_sr=sr, target_sr=16000).astype(np.float32)

    try:
        result = whisperx.align(
            segments, model_a, metadata, y_16k, device, return_char_alignments=False
        )
    except Exception as e:
        logger.error("WhisperX plain alignment failed for %s: %s", vocals_path, e, exc_info=True)
        return None

    aligned_words: list[AlignedWord] = []
    for seg_idx, seg in enumerate(result.get("segments", [])):
        for w in seg.get("words", []):
            word_start = w.get("start")
            word_end = w.get("end")
            if word_start is None or word_end is None:
                continue
            aligned_words.append(
                AlignedWord(
                    word=w.get("word", "").strip(),
                    start=round(float(word_start), 3),
                    end=round(float(word_end), 3),
                    score=round(float(w.get("score", 0.0)), 3),
                    line_index=seg_idx,
                )
            )

    if not aligned_words:
        return None

    mean_score = round(sum(w["score"] for w in aligned_words) / len(aligned_words), 3)
    return AlignmentResult(
        words=aligned_words,
        language=language,
        aligned_at=datetime.now(timezone.utc).isoformat(),
        word_count=len(aligned_words),
        line_count=len(segments),
        mean_score=mean_score,
    )
