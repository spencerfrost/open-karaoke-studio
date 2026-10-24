#!/usr/bin/env python3
"""Run one benchmark model over the test set, caching one JSON per song.

Two tasks:
- asr:   vocals in, lyrics text out. Scored by word error rate.
- align: vocals + lyrics in, a start time per line out. Each model gets the
         same blocks of lines and padded audio windows (common.build_blocks).

Production models go through the app's own functions, so they are measured
exactly as the app runs them (including reloading the model for every song).
The others get thin adapters below and load once.

Results land in results/runs/<model>/<song_id>.json. Songs that already
have a result are skipped, so a stopped run picks up where it left off;
--retry-failed reruns the ones that errored, --force reruns everything.

Run from backend/ with the venv active, one model per process so each
model's GPU memory is released when it finishes:
    python scripts/experiments/lyrics_benchmark/run_models.py whisper-small
    python scripts/experiments/lyrics_benchmark/run_models.py --list
"""

from __future__ import annotations

import argparse
import json
import logging
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

import numpy as np
from common import (
    BLOCKS_VERSION,
    RUNS_DIR,
    SAMPLE_RATE,
    Block,
    TestSong,
    load_testset,
    load_vocals_16k,
    read_run,
    reference_lines,
    run_path,
    song_blocks,
)

logger = logging.getLogger("run_models")

SongRunner = Callable[[TestSong], dict[str, Any]]


@dataclass(frozen=True)
class ModelSpec:
    task: str  # "asr" | "align"
    description: str
    load: Callable[[], SongRunner]
    reloads_per_song: bool  # timing includes model load (production path)


# ---------------------------------------------------------------------------
# ASR: the app's transcription path
# ---------------------------------------------------------------------------


def app_asr(provider: str, model_name: str) -> Callable[[], SongRunner]:
    def load() -> SongRunner:
        from app.services.lyrics_transcription import transcribe_lyrics_from_vocals

        def run(song: TestSong) -> dict[str, Any]:
            result = transcribe_lyrics_from_vocals(
                Path(song["vocals_path"]),
                language=song["language"],
                model_name=model_name,
                provider=provider,
            )
            if result is None:
                return {"error": "transcription returned nothing"}
            return {"text": result["plain_lyrics"]}

        return run

    return load


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------


def _blocks_for(song: TestSong) -> tuple[list[str], list[Block]]:
    texts = [line["text"] for line in reference_lines(song["synced_lyrics"])]
    return texts, song_blocks(song)


def _load_audio(song: TestSong) -> np.ndarray:
    return load_vocals_16k(song["vocals_path"])


def _crop(audio: np.ndarray, block: Block) -> np.ndarray:
    return audio[int(block["start"] * SAMPLE_RATE) : int(block["end"] * SAMPLE_RATE)]


def _line_starts_result(
    line_count: int, starts: dict[int, float], block_errors: list[str]
) -> dict[str, Any]:
    return {
        "line_starts": [
            round(starts[i], 3) if i in starts else None for i in range(line_count)
        ],
        "block_errors": block_errors,
        "blocks_version": BLOCKS_VERSION,
    }


def app_wav2vec2() -> SongRunner:
    """The production aligner: WhisperX's wav2vec2 model via align_line_chunks."""
    from app.services.lyrics_alignment import LineChunk, align_line_chunks

    def run(song: TestSong) -> dict[str, Any]:
        texts, blocks = _blocks_for(song)
        result = align_line_chunks(
            texts,
            [
                LineChunk(
                    first_line=b["first_line"],
                    last_line=b["last_line"],
                    start=b["start"],
                    end=b["end"],
                )
                for b in blocks
            ],
            Path(song["vocals_path"]),
            language=song["language"],
        )
        if result is None:
            return {"error": "align_line_chunks returned nothing"}
        starts: dict[int, float] = {}
        for word in result["words"]:
            starts.setdefault(word["line_index"], word["start"])
        return _line_starts_result(len(texts), starts, [])

    return run


def _mms_word(word: str) -> str:
    """Romanised lowercase letters + apostrophe: the MMS_FA alphabet."""
    stripped = "".join(
        ch
        for ch in unicodedata.normalize("NFKD", word.lower())
        if not unicodedata.combining(ch)
    )
    return "".join(ch for ch in stripped if "a" <= ch <= "z" or ch == "'")


def mms_fa() -> SongRunner:
    """Meta's MMS forced aligner (torchaudio), one model for all latin-script languages.

    Characters outside a-z and ' are dropped (accents are stripped first), so
    non-latin scripts don't work without a romaniser; such lines come back
    unaligned and count as misses.
    """
    import torch
    import torchaudio

    device = "cuda" if torch.cuda.is_available() else "cpu"
    bundle = torchaudio.pipelines.MMS_FA
    model = bundle.get_model().to(device).eval()
    tokenizer = bundle.get_tokenizer()
    aligner = bundle.get_aligner()

    def run(song: TestSong) -> dict[str, Any]:
        texts, blocks = _blocks_for(song)
        audio = _load_audio(song)
        starts: dict[int, float] = {}
        errors: list[str] = []
        for block in blocks:
            words: list[str] = []
            word_lines: list[int] = []
            for line_index in range(block["first_line"], block["last_line"] + 1):
                for raw in texts[line_index].split():
                    word = _mms_word(raw)
                    if word:
                        words.append(word)
                        word_lines.append(line_index)
            if not words:
                errors.append(f"block {block['first_line']}: no alignable words")
                continue
            try:
                waveform = torch.from_numpy(_crop(audio, block)).unsqueeze(0).to(device)
                with torch.inference_mode():
                    emission, _ = model(waveform)
                spans = aligner(emission[0], tokenizer(words))
            except Exception as exc:
                errors.append(f"block {block['first_line']}: {exc!r}")
                continue
            seconds_per_frame = waveform.size(1) / emission.size(1) / SAMPLE_RATE
            for line_index, word_spans in zip(word_lines, spans):
                starts.setdefault(
                    line_index, block["start"] + word_spans[0].start * seconds_per_frame
                )
        return _line_starts_result(len(texts), starts, errors)

    return run


def qwen3_fa() -> SongRunner:
    """Qwen3-ForcedAligner-0.6B (max 180 s of audio per call; blocks are far shorter)."""
    import torch
    from qwen_asr.inference.qwen3_forced_aligner import Qwen3ForcedAligner

    from app.services.lyrics_transcription import (
        _configure_hf_cache_environment,
        _resolve_qwen_language,
    )

    _configure_hf_cache_environment("benchmark")
    cuda = torch.cuda.is_available()
    aligner = Qwen3ForcedAligner.from_pretrained(
        "Qwen/Qwen3-ForcedAligner-0.6B",
        dtype=torch.bfloat16 if cuda else torch.float32,
        device_map="cuda" if cuda else "cpu",
    )
    supported = {lang.lower() for lang in (aligner.get_supported_languages() or [])}

    def run(song: TestSong) -> dict[str, Any]:
        language = _resolve_qwen_language(song["language"]) or "English"
        if supported and language.lower() not in supported:
            return {"error": f"language {language} not supported"}
        texts, blocks = _blocks_for(song)
        audio = _load_audio(song)
        starts: dict[int, float] = {}
        errors: list[str] = []
        for block in blocks:
            line_range = range(block["first_line"], block["last_line"] + 1)
            # The aligner returns one item per token of its own tokenisation;
            # tokenising line by line tells us which items belong to which line.
            token_lines = [
                line_index
                for line_index in line_range
                for _ in aligner.aligner_processor.encode_timestamp(
                    texts[line_index], language
                )[0]
            ]
            try:
                (result,) = aligner.align(
                    audio=(_crop(audio, block), SAMPLE_RATE),
                    text=" ".join(texts[i] for i in line_range),
                    language=language,
                )
            except Exception as exc:
                errors.append(f"block {block['first_line']}: {exc!r}")
                continue
            if len(result.items) != len(token_lines):
                errors.append(
                    f"block {block['first_line']}: {len(result.items)} items "
                    f"for {len(token_lines)} tokens"
                )
                continue
            for line_index, item in zip(token_lines, result.items):
                starts.setdefault(line_index, block["start"] + item.start_time)
        return _line_starts_result(len(texts), starts, errors)

    return run


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

MODELS: dict[str, ModelSpec] = {
    "whisper-small": ModelSpec(
        "asr",
        "WhisperX + Whisper small (app default)",
        app_asr("whisperx", "small"),
        True,
    ),
    "whisper-large-v3": ModelSpec(
        "asr", "WhisperX + Whisper large-v3", app_asr("whisperx", "large-v3"), True
    ),
    "whisper-large-v3-turbo": ModelSpec(
        "asr",
        "WhisperX + Whisper large-v3-turbo",
        app_asr("whisperx", "large-v3-turbo"),
        True,
    ),
    "qwen3-asr-1.7b": ModelSpec(
        "asr",
        "Qwen3-ASR-1.7B (app's qwen3 provider)",
        app_asr("qwen3", "Qwen/Qwen3-ASR-1.7B"),
        True,
    ),
    "qwen3-asr-0.6b": ModelSpec(
        "asr",
        "Qwen3-ASR-0.6B (app's qwen3 provider)",
        app_asr("qwen3", "Qwen/Qwen3-ASR-0.6B"),
        True,
    ),
    "wav2vec2": ModelSpec(
        "align",
        "WhisperX wav2vec2 aligner (production, align_line_chunks)",
        app_wav2vec2,
        True,
    ),
    "mms-fa": ModelSpec(
        "align", "MMS forced aligner (torchaudio MMS_FA)", mms_fa, False
    ),
    "qwen3-fa": ModelSpec("align", "Qwen3-ForcedAligner-0.6B", qwen3_fa, False),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("model", nargs="?", help="Model name (see --list)")
    parser.add_argument("--list", action="store_true", help="List models and exit")
    parser.add_argument("--limit", type=int, help="Only the first N songs (smoke test)")
    parser.add_argument(
        "--song", action="append", default=[], help="Only these song ids"
    )
    parser.add_argument(
        "--force", action="store_true", help="Rerun songs that have results"
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Rerun songs whose cached result is an error (e.g. out of GPU memory)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    # The app's services log every step at INFO; keep the benchmark's own lines readable.
    logging.getLogger("app").setLevel(logging.WARNING)

    if args.list or not args.model:
        for name, spec in MODELS.items():
            print(f"{name:24} {spec.task:6} {spec.description}")
        return
    spec = MODELS.get(args.model)
    if spec is None:
        raise SystemExit(f"Unknown model {args.model!r}; see --list")

    songs = load_testset()
    if args.song:
        songs = [s for s in songs if s["song_id"] in set(args.song)]
    if args.limit:
        songs = songs[: args.limit]

    def needs_run(song: TestSong) -> bool:
        if args.force:
            return True
        previous = read_run(args.model, song["song_id"])
        return previous is None or (args.retry_failed and "error" in previous)

    pending = [s for s in songs if needs_run(s)]
    logger.info("%s: %d songs, %d to run", args.model, len(songs), len(pending))
    if not pending:
        return

    load_started = perf_counter()
    runner = spec.load()
    logger.info("Loaded in %.1fs", perf_counter() - load_started)

    out_dir = RUNS_DIR / args.model
    out_dir.mkdir(parents=True, exist_ok=True)
    for number, song in enumerate(pending, 1):
        if spec.task == "align":
            song_blocks(song)  # cached before timing, so sec/song is the model's
        started = perf_counter()
        try:
            output = runner(song)
        except Exception as exc:
            logger.exception("Failed on %s", song["song_id"])
            output = {"error": repr(exc)}
        elapsed = perf_counter() - started
        record = {
            "model": args.model,
            "task": spec.task,
            "song_id": song["song_id"],
            "elapsed_s": round(elapsed, 2),
            "includes_model_load": spec.reloads_per_song,
            "ran_at": datetime.now(timezone.utc).isoformat(),
            **output,
        }
        run_path(args.model, song["song_id"]).write_text(
            json.dumps(record, indent=2, ensure_ascii=False)
        )
        logger.info(
            "[%d/%d] %.1fs %s — %s%s",
            number,
            len(pending),
            elapsed,
            song["artist"],
            song["title"],
            f"  ERROR: {output['error']}" if "error" in output else "",
        )
        if spec.reloads_per_song:
            _release_gpu_memory()


def _release_gpu_memory() -> None:
    """Free the model a production path loaded for one song.

    The WhisperX path doesn't release VRAM when it returns (the app relies
    on gpu_idle_cleanup after 30 idle minutes), so without this a run of
    whisper-large-v3 fills the card within a few songs and the rest fail
    with CUDA out of memory.
    """
    import gc

    import torch

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
