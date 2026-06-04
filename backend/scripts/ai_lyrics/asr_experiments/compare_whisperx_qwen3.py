#!/usr/bin/env python3
"""Compare WhisperX and Qwen3-ASR outputs across multiple vocals tracks."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[3]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.lyrics_transcription import transcribe_lyrics_from_vocals


@dataclass
class RunRow:
    provider: str
    vocals_path: str
    song_id: str
    ok: bool
    elapsed_ms: float
    line_count: int
    word_count: int
    mean_score: float
    language: str
    model: str
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare WhisperX and Qwen3-ASR on multiple vocals tracks")
    parser.add_argument("--vocals", action="append", default=[], help="Path to vocals.mp3 (repeatable)")
    parser.add_argument("--song-id", action="append", default=[], help="Song id in karaoke_library (repeatable)")
    parser.add_argument(
        "--providers",
        default="whisperx,qwen3",
        help="Comma-separated ASR providers. Supported: whisperx,qwen3",
    )
    parser.add_argument("--language", default="en", help="ASR language hint (default: en)")
    parser.add_argument("--sample", type=int, default=0, help="Randomly sample N songs from karaoke_library")
    parser.add_argument("--seed", type=int, default=1337, help="Random seed for --sample")
    parser.add_argument(
        "--library-dir",
        default=os.getenv("LIBRARY_DIR", str(BACKEND_DIR.parent / "karaoke_library")),
        help="Path to karaoke_library",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent / "results"),
        help="Directory to write comparison JSON/CSV files",
    )
    return parser.parse_args()


def collect_vocals_paths(args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    library_dir = Path(args.library_dir).expanduser().resolve()

    def add_path(path: Path) -> None:
        resolved = path.expanduser().resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        paths.append(resolved)

    for vocals_arg in args.vocals:
        add_path(Path(vocals_arg))

    for song_id in args.song_id:
        add_path(library_dir / song_id / "vocals.mp3")

    if args.sample > 0:
        candidates = sorted(library_dir.glob("*/vocals.mp3"))
        rng = random.Random(args.seed)
        sample_size = min(args.sample, len(candidates))
        for sampled in rng.sample(candidates, k=sample_size):
            add_path(sampled)

    return [path for path in paths if path.exists()]


def summarize(rows: list[RunRow]) -> dict[str, Any]:
    providers = sorted(set(row.provider for row in rows))
    summary: dict[str, Any] = {}
    for provider in providers:
        provider_rows = [row for row in rows if row.provider == provider]
        ok_rows = [row for row in provider_rows if row.ok]
        summary[provider] = {
            "runs": len(provider_rows),
            "successes": len(ok_rows),
            "success_rate": round(len(ok_rows) / len(provider_rows), 3) if provider_rows else 0.0,
            "avg_elapsed_ms": round(mean(row.elapsed_ms for row in ok_rows), 1) if ok_rows else None,
            "avg_line_count": round(mean(row.line_count for row in ok_rows), 1) if ok_rows else None,
            "avg_word_count": round(mean(row.word_count for row in ok_rows), 1) if ok_rows else None,
            "avg_mean_score": round(mean(row.mean_score for row in ok_rows), 3) if ok_rows else None,
        }
    return summary


def run_one(provider: str, vocals_path: Path, language: str) -> RunRow:
    song_id = vocals_path.parent.name
    started_at = perf_counter()
    try:
        transcription = transcribe_lyrics_from_vocals(
            vocals_path=vocals_path,
            language=language,
            provider=provider,
        )
    except Exception as exc:
        elapsed_ms = round((perf_counter() - started_at) * 1000, 1)
        return RunRow(
            provider=provider,
            vocals_path=str(vocals_path),
            song_id=song_id,
            ok=False,
            elapsed_ms=elapsed_ms,
            line_count=0,
            word_count=0,
            mean_score=0.0,
            language="unknown",
            model="unknown",
            error=str(exc),
        )

    elapsed_ms = round((perf_counter() - started_at) * 1000, 1)
    if not transcription:
        return RunRow(
            provider=provider,
            vocals_path=str(vocals_path),
            song_id=song_id,
            ok=False,
            elapsed_ms=elapsed_ms,
            line_count=0,
            word_count=0,
            mean_score=0.0,
            language="unknown",
            model="unknown",
            error="No transcription result",
        )

    alignment = transcription.get("alignment", {})
    return RunRow(
        provider=str(transcription.get("asr_provider", provider)),
        vocals_path=str(vocals_path),
        song_id=song_id,
        ok=True,
        elapsed_ms=elapsed_ms,
        line_count=int(alignment.get("line_count", 0) or 0),
        word_count=int(alignment.get("word_count", 0) or 0),
        mean_score=float(alignment.get("mean_score", 0.0) or 0.0),
        language=str(alignment.get("language", "unknown")),
        model=str(transcription.get("asr_model", alignment.get("asr_model", "unknown"))),
        error=None,
    )


def write_outputs(rows: list[RunRow], summary: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"asr_compare_{timestamp}.json"
    csv_path = output_dir / f"asr_compare_{timestamp}.csv"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "runs": [row.__dict__ for row in rows],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "provider",
                "song_id",
                "vocals_path",
                "ok",
                "elapsed_ms",
                "line_count",
                "word_count",
                "mean_score",
                "language",
                "model",
                "error",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)

    return json_path, csv_path


def main() -> int:
    args = parse_args()
    providers = [item.strip().lower() for item in args.providers.split(",") if item.strip()]
    if not providers:
        print("No providers selected. Use --providers whisperx,qwen3")
        return 1

    vocals_paths = collect_vocals_paths(args)
    if not vocals_paths:
        print("No vocals files found. Provide --vocals, --song-id, or --sample.")
        return 1

    print(f"Running ASR comparison for {len(vocals_paths)} tracks with providers: {', '.join(providers)}")
    rows: list[RunRow] = []

    for vocals_path in vocals_paths:
        print(f"\nTrack: {vocals_path}")
        for provider in providers:
            print(f"  - Provider {provider} ...", end="", flush=True)
            row = run_one(provider=provider, vocals_path=vocals_path, language=args.language)
            rows.append(row)
            status = "ok" if row.ok else "failed"
            print(f" {status} ({row.elapsed_ms} ms)")

    summary = summarize(rows)
    json_path, csv_path = write_outputs(rows=rows, summary=summary, output_dir=Path(args.output_dir).expanduser().resolve())

    print("\nSummary")
    print(json.dumps(summary, indent=2))
    print(f"\nDetailed JSON: {json_path}")
    print(f"Detailed CSV: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
