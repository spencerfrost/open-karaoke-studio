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
import os
from pathlib import Path
from time import perf_counter
from typing import Literal, TypedDict

import numpy as np
from app.services.audio import load_vocals
from app.services.gpu_idle_cleanup import begin_gpu_activity, end_gpu_activity
from app.services.lyrics_analysis import LrcLine, parse_lrc_lines
from app.services.lyrics_timing import log_lyrics_event

logger = logging.getLogger(__name__)


_INSTR_MIN_GAP_SECONDS = 6.0
_INSTR_LEAD_IN_SECONDS = 1.5


def _song_id_from_vocals_path(vocals_path: Path) -> str:
    return vocals_path.parent.name


def _is_cuda_device(device: str) -> bool:
    return str(device).lower().startswith("cuda")


def _resolve_alignment_device(device: str | None = None) -> str:
    requested_device = (device or os.getenv("LYRICS_ALIGNMENT_DEVICE", "auto")).strip()
    if not requested_device:
        requested_device = "auto"

    if requested_device.lower() != "auto":
        return requested_device

    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        logger.warning(
            "Falling back to CPU for lyrics alignment device resolution", exc_info=True
        )
        return "cpu"


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class AlignedWord(TypedDict):
    word: str
    start: float  # seconds
    end: float  # seconds
    score: float
    line_index: int  # which LRC line this word belongs to


class InstrumentalInterval(TypedDict):
    start: float  # seconds
    end: float  # seconds
    duration: float  # seconds
    lead_in_start: float  # seconds
    next_line_index: int  # line index of next lyric line
    confidence: float
    source: str


class AlignmentResult(TypedDict):
    words: list[AlignedWord]
    instrumental_intervals: list[InstrumentalInterval]
    language: str
    aligned_at: str
    word_count: int
    line_count: int
    mean_score: float  # average confidence across all aligned words


SyncedAlignmentMode = Literal[
    "synced_strict",
    "synced_padded_small",
    "synced_padded_medium",
    "synced_stripped_plain",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _lrc_lines_to_segments(
    lrc_lines: list[LrcLine],
    *,
    pad_before: float = 0.0,
    pad_after: float = 0.0,
) -> list[dict]:
    """
    Convert parsed LRC lines into the segment format expected by whisperx.align().

    Each segment needs "text", "start" (seconds), and "end" (seconds).
    For the end time, use the next line's start timestamp.
    The final line gets a generous 10-second window.
    """
    segments = []
    content_lines = [l for l in lrc_lines if l["text"].strip()]

    for i, line in enumerate(content_lines):
        start_s = max(0.0, line["timestamp"] - pad_before)

        if i + 1 < len(content_lines):
            # End at next line's start, clamped to at least 0.5s window
            end_s = max(start_s + 0.5, content_lines[i + 1]["timestamp"] + pad_after)
        else:
            end_s = start_s + 10.0 + pad_after  # generous window for the last line

        segments.append(
            {
                "text": line["text"].strip(),
                "start": start_s,
                "end": end_s,
            }
        )

    return segments


def _content_line_indices(lrc_lines: list[LrcLine]) -> list[int]:
    """
    Positions within `lrc_lines` (which includes blank lines) of each
    non-blank line, in order. This is the source-line index convention every
    alignment path stores against.
    """
    return [orig_idx for orig_idx, line in enumerate(lrc_lines) if line["text"].strip()]


def _segments_to_input_tokens(
    segments: list[dict], line_indices: list[int]
) -> list[tuple[int, str]]:
    """
    Flatten segment text into (source_line_index, word) pairs in the same
    order whisperx.align() concatenates its output word_segments — segment by
    segment, left to right within each segment's text.
    """
    tokens: list[tuple[int, str]] = []
    for line_index, segment in zip(line_indices, segments):
        tokens.extend((line_index, word) for word in segment["text"].split())
    return tokens


def _flatten_output_words(result_segments: list[dict]) -> list[dict]:
    words: list[dict] = []
    for seg in result_segments:
        words.extend(seg.get("words", []))
    return words


def _assign_line_indices(
    result_segments: list[dict],
    input_tokens: list[tuple[int, str]],
) -> list[AlignedWord] | None:
    """
    Pair WhisperX's flattened output words with the flattened input tokens
    positionally, taking the line index from the input side.

    Forced alignment aligns known text: WhisperX never adds, drops, or
    reorders words, it only re-groups them into different output segments
    (splitting one input line into several sentences, or merging several back
    together — see whisperx/alignment.py's sentence-split + groupby). That
    makes position the only reliable key; `seg_idx` on the output side is
    not, since a single split shifts every line index after it.

    Compares word text while walking as a safety net. Returns None on the
    first mismatch (word count or text divergence) so the caller can fall
    back to the old segment-position behaviour rather than store a mapping
    that is wrong in some new way.
    """
    output_words = _flatten_output_words(result_segments)
    if len(output_words) != len(input_tokens):
        logger.warning(
            "Line-index token walk: %d output words vs %d input tokens, falling back",
            len(output_words),
            len(input_tokens),
        )
        return None

    aligned_words: list[AlignedWord] = []
    for position, (output_word, (line_index, input_token)) in enumerate(
        zip(output_words, input_tokens)
    ):
        output_text = output_word.get("word", "").strip()
        if output_text != input_token:
            logger.warning(
                "Line-index token walk: mismatch at position %d ('%s' vs '%s'), falling back",
                position,
                output_text,
                input_token,
            )
            return None

        word_start = output_word.get("start")
        word_end = output_word.get("end")
        if word_start is None or word_end is None:
            continue

        aligned_words.append(
            AlignedWord(
                word=output_text,
                start=round(float(word_start), 3),
                end=round(float(word_end), 3),
                score=round(float(output_word.get("score", 0.0)), 3),
                line_index=line_index,
            )
        )

    return aligned_words


def _assign_line_indices_by_segment_position(
    result_segments: list[dict], line_indices: list[int]
) -> list[AlignedWord]:
    """
    Legacy fallback: trust WhisperX's output segment position as the line
    index. Wrong whenever WhisperX splits or merges a segment — kept only so
    a token-walk mismatch cannot silently store a mapping worse than before
    this fix existed.
    """
    aligned_words: list[AlignedWord] = []
    for seg_idx, seg in enumerate(result_segments):
        line_index = line_indices[seg_idx] if seg_idx < len(line_indices) else seg_idx
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
                    line_index=line_index,
                )
            )
    return aligned_words


def recompute_alignment_line_indices(
    words: list[AlignedWord],
    *,
    source_type: Literal["plain", "synced"],
    content: str,
) -> list[AlignedWord] | None:
    """
    Offline equivalent of _assign_line_indices for the backfill script: given
    an already-aligned word list (correct timings, wrong line_index) and the
    original lyrics text, re-derive line_index from word position alone — no
    audio, no GPU, no re-running WhisperX.

    Works because the stored `words` array is already in the positional order
    WhisperX produced it in, which is the same order `_segments_to_input_tokens`
    reconstructs from the source text. Returns None if the token walk diverges
    (count or text mismatch) so the caller can skip the song rather than store
    a worse mapping.
    """
    if source_type == "synced":
        lrc_lines = parse_lrc_lines(content)
        content_line_indices = _content_line_indices(lrc_lines)
        segments = [
            {"text": line["text"].strip()} for line in lrc_lines if line["text"].strip()
        ]
    else:
        segments = _plain_lines_to_segments(content)
        content_line_indices = list(range(len(segments)))

    input_tokens = _segments_to_input_tokens(segments, content_line_indices)
    if len(input_tokens) != len(words):
        return None

    recomputed: list[AlignedWord] = []
    for (line_index, input_token), word in zip(input_tokens, words):
        if word["word"].strip() != input_token:
            return None
        recomputed.append(
            AlignedWord(
                word=word["word"],
                start=word["start"],
                end=word["end"],
                score=word["score"],
                line_index=line_index,
            )
        )
    return recomputed


def _synced_lrc_to_plain_text(lrc_content: str) -> str:
    """Strip timestamps from synced lyrics while preserving line order."""
    lrc_lines = parse_lrc_lines(lrc_content)
    return "\n".join(line["text"].strip() for line in lrc_lines if line["text"].strip())


def _get_synced_alignment_mode_config(
    mode: SyncedAlignmentMode,
) -> dict[str, float | str]:
    if mode == "synced_strict":
        return {"alignment_mode": "synced", "pad_before": 0.0, "pad_after": 0.0}
    if mode == "synced_padded_small":
        return {
            "alignment_mode": "synced_padded_small",
            "pad_before": 3.0,
            "pad_after": 3.0,
        }
    if mode == "synced_padded_medium":
        return {
            "alignment_mode": "synced_padded_medium",
            "pad_before": 8.0,
            "pad_after": 8.0,
        }
    if mode == "synced_stripped_plain":
        return {
            "alignment_mode": "synced_stripped_plain",
            "pad_before": 0.0,
            "pad_after": 0.0,
        }
    raise ValueError(f"Unsupported synced alignment mode: {mode}")


def _build_instrumental_intervals(
    aligned_words: list[AlignedWord],
    *,
    min_gap_seconds: float = _INSTR_MIN_GAP_SECONDS,
    lead_in_seconds: float = _INSTR_LEAD_IN_SECONDS,
) -> list[InstrumentalInterval]:
    """
    Derive instrumental windows from lyric-free gaps between aligned words.

    An intro is not a special case: the walk is seeded with a virtual word
    ending at 0.0s, so the gap before the first real word is just another gap
    judged by the same threshold as every gap between verses. This
    intentionally favors precision over recall — cues must be clearly long
    breaks so we avoid false positives from repeated tails, ad-libs, and
    missed low-register words.
    """
    if not aligned_words:
        return []

    sorted_words = sorted(aligned_words, key=lambda w: (w["start"], w["end"]))
    intervals: list[InstrumentalInterval] = []

    lead_word = AlignedWord(
        word="", start=0.0, end=0.0, score=1.0, line_index=sorted_words[0]["line_index"]
    )
    for current_word, next_word in zip([lead_word, *sorted_words], sorted_words):
        gap_start = current_word["end"]
        gap_end = next_word["start"]
        gap_duration = gap_end - gap_start

        # Ignore micro-pauses and pauses that stay within a single lyric line.
        if gap_duration < min_gap_seconds:
            continue
        if (
            current_word is not lead_word
            and next_word["line_index"] == current_word["line_index"]
        ):
            continue

        lead_in_start = max(gap_start, gap_end - lead_in_seconds)
        intervals.append(
            InstrumentalInterval(
                start=round(gap_start, 3),
                end=round(gap_end, 3),
                duration=round(gap_duration, 3),
                lead_in_start=round(lead_in_start, 3),
                next_line_index=next_word["line_index"],
                confidence=round(min(1.0, gap_duration / 8.0), 3),
                source="whisperx_gap",
            )
        )

    return intervals


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def align_lyrics_to_vocals(
    lrc_content: str,
    vocals_path: Path,
    language: str = "en",
    device: str = "auto",
    pad_before: float = 0.0,
    pad_after: float = 0.0,
    alignment_mode: str = "synced",
) -> AlignmentResult | None:
    """
    Align LRC lyrics to vocals audio using WhisperX forced alignment.

    Loads the wav2vec2 phoneme alignment model (downloaded on first use),
    constructs segments from the LRC lines, and runs forced alignment.
    Returns word-level timestamps with their originating line index.

    Returns None if alignment fails or produces no words.
    """
    from datetime import datetime, timezone

    import whisperx

    device = _resolve_alignment_device(device)
    lrc_lines = parse_lrc_lines(lrc_content)
    song_id = _song_id_from_vocals_path(vocals_path)
    if not lrc_lines:
        logger.warning("align_lyrics_to_vocals: no LRC lines found")
        log_lyrics_event(song_id, "lyrics_lrc_parse_empty")
        return None

    content_lines = [l for l in lrc_lines if l["text"].strip()]
    if not content_lines:
        logger.warning("align_lyrics_to_vocals: no non-blank LRC lines found")
        log_lyrics_event(song_id, "lyrics_lrc_content_empty")
        return None

    # Load audio
    logger.info("Loading vocals from %s", vocals_path)
    audio_load_started_at = perf_counter()
    y, sr = load_vocals(vocals_path)
    log_lyrics_event(
        song_id,
        "lyrics_audio_loaded",
        alignment_mode=alignment_mode,
        elapsed_ms=round((perf_counter() - audio_load_started_at) * 1000, 1),
        sample_rate=sr,
    )
    # WhisperX expects float32 numpy array at 16kHz
    import librosa

    resample_started_at = perf_counter()
    y_16k = librosa.resample(y, orig_sr=sr, target_sr=16000).astype(np.float32)
    log_lyrics_event(
        song_id,
        "lyrics_audio_resampled",
        alignment_mode=alignment_mode,
        elapsed_ms=round((perf_counter() - resample_started_at) * 1000, 1),
        sample_count=len(y_16k),
    )

    # Build segments and line mapping
    segments = _lrc_lines_to_segments(
        lrc_lines, pad_before=pad_before, pad_after=pad_after
    )
    content_line_indices = _content_line_indices(lrc_lines)

    if not segments:
        logger.warning("align_lyrics_to_vocals: no segments constructed")
        log_lyrics_event(
            song_id, "lyrics_segments_empty", alignment_mode=alignment_mode
        )
        return None

    logger.info(
        "Running forced alignment for %d segments (language=%s, device=%s)",
        len(segments),
        language,
        device,
    )

    activity_started = False
    model_load_started_at = perf_counter()
    try:
        if _is_cuda_device(device):
            begin_gpu_activity(f"lyrics-alignment:{language}")
            activity_started = True
        model_a, metadata = whisperx.load_align_model(
            language_code=language, device=device
        )
        log_lyrics_event(
            song_id,
            "lyrics_model_loaded",
            alignment_mode=alignment_mode,
            elapsed_ms=round((perf_counter() - model_load_started_at) * 1000, 1),
            language=language,
            device=device,
        )
        align_started_at = perf_counter()
        result = whisperx.align(
            segments,
            model_a,
            metadata,
            y_16k,
            device,
            return_char_alignments=False,
        )
        log_lyrics_event(
            song_id,
            "lyrics_whisperx_align_finished",
            alignment_mode=alignment_mode,
            elapsed_ms=round((perf_counter() - align_started_at) * 1000, 1),
            segment_count=len(segments),
        )
    except Exception as e:
        logger.error("WhisperX alignment failed: %s", e, exc_info=True)
        log_lyrics_event(
            song_id, "lyrics_whisperx_align_failed", alignment_mode=alignment_mode
        )
        return None
    finally:
        if activity_started:
            end_gpu_activity(f"lyrics-alignment:{language}")

    # Flatten words from all segments, tagging each with its line index by
    # walking them positionally alongside the input tokens (see
    # _assign_line_indices) rather than trusting the output segment position,
    # which WhisperX's sentence-splitting can shift.
    result_segments = result.get("segments", [])
    input_tokens = _segments_to_input_tokens(segments, content_line_indices)
    aligned_words = _assign_line_indices(result_segments, input_tokens)
    if aligned_words is None:
        aligned_words = _assign_line_indices_by_segment_position(
            result_segments, content_line_indices
        )

    if not aligned_words:
        logger.warning("align_lyrics_to_vocals: alignment produced no words")
        log_lyrics_event(
            song_id, "lyrics_alignment_empty", alignment_mode=alignment_mode
        )
        return None

    logger.info(
        "Alignment complete: %d words across %d lines",
        len(aligned_words),
        len(content_lines),
    )
    log_lyrics_event(
        song_id,
        "lyrics_alignment_words_ready",
        alignment_mode=alignment_mode,
        word_count=len(aligned_words),
        line_count=len(content_lines),
    )

    mean_score = round(sum(w["score"] for w in aligned_words) / len(aligned_words), 3)
    instrumental_intervals = _build_instrumental_intervals(aligned_words)

    return AlignmentResult(
        words=aligned_words,
        instrumental_intervals=instrumental_intervals,
        language=language,
        aligned_at=datetime.now(timezone.utc).isoformat(),
        word_count=len(aligned_words),
        line_count=len(content_lines),
        mean_score=mean_score,
    )


def align_synced_lyrics_to_vocals(
    lrc_content: str,
    vocals_path: Path,
    language: str = "en",
    device: str = "auto",
    mode: SyncedAlignmentMode = "synced_strict",
) -> AlignmentResult | None:
    """Align synced lyrics using one of several timestamp-aware or stripped modes."""
    config = _get_synced_alignment_mode_config(mode)
    if mode == "synced_stripped_plain":
        lrc_lines = parse_lrc_lines(lrc_content)
        content_line_indices = _content_line_indices(lrc_lines)
        plain_text = _synced_lrc_to_plain_text(lrc_content)
        return align_plain_lyrics_to_vocals(
            plain_text,
            vocals_path,
            language=language,
            device=device,
            alignment_mode=str(config["alignment_mode"]),
            line_indices=content_line_indices,
        )

    return align_lyrics_to_vocals(
        lrc_content,
        vocals_path,
        language=language,
        device=device,
        pad_before=float(config["pad_before"]),
        pad_after=float(config["pad_after"]),
        alignment_mode=str(config["alignment_mode"]),
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
    device: str = "auto",
    alignment_mode: str = "plain",
    line_indices: list[int] | None = None,
) -> AlignmentResult | None:
    """
    Align plain text lyrics to vocals using WhisperX forced alignment.

    Uses evenly-spaced dummy timestamps as segment scaffolding — the wav2vec2
    alignment model finds the actual timing. Returns the same AlignmentResult
    as align_lyrics_to_vocals; line_index in AlignedWord maps to the stripped
    line list (section headers excluded), unless `line_indices` is given —
    used by align_synced_lyrics_to_vocals's synced_stripped_plain mode to tag
    words with their original LRC line directly instead of remapping after
    the fact.
    """
    from datetime import datetime, timezone

    import whisperx

    device = _resolve_alignment_device(device)
    segments = _plain_lines_to_segments(plain_content)
    song_id = _song_id_from_vocals_path(vocals_path)
    if not segments:
        logger.warning("align_plain_lyrics_to_vocals: no usable lines found")
        log_lyrics_event(song_id, "lyrics_plain_segments_empty")
        return None

    resolved_line_indices = (
        line_indices if line_indices is not None else list(range(len(segments)))
    )

    logger.info("Loading vocals from %s", vocals_path)
    audio_load_started_at = perf_counter()
    y, sr = load_vocals(vocals_path)
    log_lyrics_event(
        song_id,
        "lyrics_audio_loaded",
        alignment_mode=alignment_mode,
        elapsed_ms=round((perf_counter() - audio_load_started_at) * 1000, 1),
        sample_rate=sr,
    )
    import librosa

    resample_started_at = perf_counter()
    y_16k = librosa.resample(y, orig_sr=sr, target_sr=16000).astype(np.float32)
    log_lyrics_event(
        song_id,
        "lyrics_audio_resampled",
        alignment_mode=alignment_mode,
        elapsed_ms=round((perf_counter() - resample_started_at) * 1000, 1),
        sample_count=len(y_16k),
    )

    logger.info(
        "Running plain-text forced alignment for %d lines (language=%s, device=%s)",
        len(segments),
        language,
        device,
    )

    activity_started = False
    model_load_started_at = perf_counter()
    try:
        if _is_cuda_device(device):
            begin_gpu_activity(f"plain-lyrics-alignment:{language}")
            activity_started = True
        model_a, metadata = whisperx.load_align_model(
            language_code=language, device=device
        )
        log_lyrics_event(
            song_id,
            "lyrics_model_loaded",
            alignment_mode=alignment_mode,
            elapsed_ms=round((perf_counter() - model_load_started_at) * 1000, 1),
            language=language,
            device=device,
        )
        align_started_at = perf_counter()
        result = whisperx.align(
            segments,
            model_a,
            metadata,
            y_16k,
            device,
            return_char_alignments=False,
        )
        log_lyrics_event(
            song_id,
            "lyrics_whisperx_align_finished",
            alignment_mode=alignment_mode,
            elapsed_ms=round((perf_counter() - align_started_at) * 1000, 1),
            segment_count=len(segments),
        )
    except Exception as e:
        logger.error("WhisperX plain alignment failed: %s", e, exc_info=True)
        log_lyrics_event(
            song_id, "lyrics_whisperx_align_failed", alignment_mode=alignment_mode
        )
        return None
    finally:
        if activity_started:
            end_gpu_activity(f"plain-lyrics-alignment:{language}")

    result_segments = result.get("segments", [])
    input_tokens = _segments_to_input_tokens(segments, resolved_line_indices)
    aligned_words = _assign_line_indices(result_segments, input_tokens)
    if aligned_words is None:
        aligned_words = _assign_line_indices_by_segment_position(
            result_segments, resolved_line_indices
        )

    if not aligned_words:
        logger.warning("align_plain_lyrics_to_vocals: alignment produced no words")
        log_lyrics_event(
            song_id, "lyrics_alignment_empty", alignment_mode=alignment_mode
        )
        return None

    mean_score = round(sum(w["score"] for w in aligned_words) / len(aligned_words), 3)
    instrumental_intervals = _build_instrumental_intervals(aligned_words)

    logger.info(
        "Plain alignment complete: %d words, mean_score=%.3f",
        len(aligned_words),
        mean_score,
    )
    log_lyrics_event(
        song_id,
        "lyrics_alignment_words_ready",
        alignment_mode=alignment_mode,
        word_count=len(aligned_words),
        line_count=len(segments),
        mean_score=mean_score,
    )

    return AlignmentResult(
        words=aligned_words,
        instrumental_intervals=instrumental_intervals,
        language=language,
        aligned_at=datetime.now(timezone.utc).isoformat(),
        word_count=len(aligned_words),
        line_count=len(segments),
        mean_score=mean_score,
    )


# ---------------------------------------------------------------------------
# Batch-friendly: shared model loading
# ---------------------------------------------------------------------------


def load_alignment_model(language: str = "en", device: str = "auto"):
    """
    Load the WhisperX wav2vec2 alignment model once for reuse across many songs.

    Returns (model_a, metadata) — pass these to align_*_with_model() to avoid
    reloading the ~360 MB model for every song in a batch operation.
    """
    import whisperx

    device = _resolve_alignment_device(device)
    logger.info(
        "Loading WhisperX alignment model (language=%s, device=%s)", language, device
    )
    return whisperx.load_align_model(language_code=language, device=device)


def align_lyrics_to_vocals_with_model(
    lrc_content: str,
    vocals_path: Path,
    model_a,
    metadata,
    language: str = "en",
    device: str = "auto",
) -> AlignmentResult | None:
    """
    Align LRC lyrics using a pre-loaded WhisperX model.

    Identical to align_lyrics_to_vocals() but accepts an already-loaded
    (model_a, metadata) pair so the model is not reloaded per song.
    """
    from datetime import datetime, timezone

    import whisperx

    device = _resolve_alignment_device(device)
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
    content_line_indices = _content_line_indices(lrc_lines)

    if not segments:
        return None

    try:
        result = whisperx.align(
            segments, model_a, metadata, y_16k, device, return_char_alignments=False
        )
    except Exception as e:
        logger.error(
            "WhisperX alignment failed for %s: %s", vocals_path, e, exc_info=True
        )
        return None

    result_segments = result.get("segments", [])
    input_tokens = _segments_to_input_tokens(segments, content_line_indices)
    aligned_words = _assign_line_indices(result_segments, input_tokens)
    if aligned_words is None:
        aligned_words = _assign_line_indices_by_segment_position(
            result_segments, content_line_indices
        )

    if not aligned_words:
        return None

    mean_score = round(sum(w["score"] for w in aligned_words) / len(aligned_words), 3)
    instrumental_intervals = _build_instrumental_intervals(aligned_words)
    return AlignmentResult(
        words=aligned_words,
        instrumental_intervals=instrumental_intervals,
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
    device: str = "auto",
) -> AlignmentResult | None:
    """
    Align plain text lyrics using a pre-loaded WhisperX model.

    Identical to align_plain_lyrics_to_vocals() but accepts an already-loaded
    (model_a, metadata) pair so the model is not reloaded per song.
    """
    from datetime import datetime, timezone

    import whisperx

    device = _resolve_alignment_device(device)
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
        logger.error(
            "WhisperX plain alignment failed for %s: %s", vocals_path, e, exc_info=True
        )
        return None

    line_indices = list(range(len(segments)))
    result_segments = result.get("segments", [])
    input_tokens = _segments_to_input_tokens(segments, line_indices)
    aligned_words = _assign_line_indices(result_segments, input_tokens)
    if aligned_words is None:
        aligned_words = _assign_line_indices_by_segment_position(
            result_segments, line_indices
        )

    if not aligned_words:
        return None

    mean_score = round(sum(w["score"] for w in aligned_words) / len(aligned_words), 3)
    instrumental_intervals = _build_instrumental_intervals(aligned_words)
    return AlignmentResult(
        words=aligned_words,
        instrumental_intervals=instrumental_intervals,
        language=language,
        aligned_at=datetime.now(timezone.utc).isoformat(),
        word_count=len(aligned_words),
        line_count=len(segments),
        mean_score=mean_score,
    )
