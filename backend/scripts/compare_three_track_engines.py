#!/usr/bin/env python3
"""
Compare Demucs-based vs Roformer-based three-track separation engines.

Runs both pipelines on the same source audio and writes outputs to an isolated
directory for manual A/B listening. Does not modify karaoke_library or the DB.

Usage:
    cd backend && source venv/bin/activate
    python scripts/compare_three_track_engines.py --sample 5 --output-dir ../three_track_compare_test
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import os
import random
import shutil
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch
from app.services.separation_engines.roformer_three_track import (
    separate_with_three_track as roformer_three_track,
)
from app.services.separation_engines.three_track import (
    separate_with_three_track as demucs_three_track,
)
from app.services.separation_engines.three_track_duality_v2 import (
    separate_with_three_track_duality_v2,
)
from app.services.separation_engines.three_track_mel1143 import (
    separate_with_three_track_mel1143,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

STEM_FILES = ("vocals.mp3", "backing_vocals.mp3", "instrumental.mp3")

README_TEXT = """Three-Track Engine Listening Comparison
==========================================

For each song folder, compare the same stem across engines:

  {song_id}/demucs_three_track/vocals.mp3
  {song_id}/roformer_three_track/vocals.mp3

Stems: vocals.mp3 (lead), backing_vocals.mp3, instrumental.mp3
Reference mix: {song_id}/original.mp3

Fairness note (as-run):
- demucs_three_track: Demucs primary + Roformer karaoke + de-noise on backing
- roformer_three_track: Roformer primary + Roformer karaoke + de-noise disabled
- three_track_duality_v2: Demucs primary + InstVoc Duality V2 vocal split + de-noise on backing
- three_track_mel1143: Demucs primary + Mel-Roformer-Viperx-1143 vocal split + de-noise on backing

Backing vocal A/B is not apples-to-apples on the polish step; focus lead vocal
and instrumental when judging the Roformer-primary upgrade.

See manifest.json for timings, success flags, and errors.
"""

ENGINES: list[tuple[str, Callable[..., bool]]] = [
    ("demucs_three_track", demucs_three_track),
    ("roformer_three_track", roformer_three_track),
    ("three_track_duality_v2", separate_with_three_track_duality_v2),
    ("three_track_mel1143", separate_with_three_track_mel1143),
]


@dataclass
class EngineRunResult:
    engine: str
    success: bool
    duration_seconds: float
    output_dir: str
    stems_present: dict[str, bool]
    error: str | None = None


@dataclass
class SongResult:
    song_id: str
    title: str | None
    input_path: str
    original_copied: bool
    engines: list[EngineRunResult]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Demucs vs Roformer three-track separation engines",
    )
    parser.add_argument(
        "--song-id",
        action="append",
        default=[],
        help="Song UUID in karaoke_library (repeatable)",
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="Standalone audio file path (repeatable); song_id = file stem",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=0,
        help="Randomly sample N songs that have original.mp3 in library",
    )
    parser.add_argument("--seed", type=int, default=1337, help="RNG seed for --sample")
    parser.add_argument(
        "--library-dir",
        default=os.getenv("LIBRARY_DIR", str(REPO_ROOT / "karaoke_library")),
        help="Path to karaoke_library",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output root (default: ../three_track_compare_<timestamp>)",
    )
    return parser.parse_args()


def load_song_title(song_dir: Path) -> str | None:
    metadata_path = song_dir / "metadata.json"
    if not metadata_path.exists():
        return None
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        title = data.get("title") or data.get("name")
        return str(title) if title else None
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read metadata for %s: %s", song_dir.name, exc)
        return None


def collect_jobs(args: argparse.Namespace) -> list[tuple[str, Path, str | None]]:
    """
    Return list of (song_id, input_path, title_or_none).
    """
    library_dir = Path(args.library_dir).expanduser().resolve()
    jobs: list[tuple[str, Path, str | None]] = []
    seen_ids: set[str] = set()

    def add_job(song_id: str, input_path: Path, title: str | None) -> None:
        if song_id in seen_ids:
            return
        if not input_path.exists():
            logger.warning("Skipping %s: input not found at %s", song_id, input_path)
            return
        seen_ids.add(song_id)
        jobs.append((song_id, input_path, title))

    for song_id in args.song_id:
        song_dir = library_dir / song_id
        add_job(song_id, song_dir / "original.mp3", load_song_title(song_dir))

    for input_arg in args.input:
        input_path = Path(input_arg).expanduser().resolve()
        song_id = input_path.stem
        add_job(song_id, input_path, None)

    if args.sample > 0:
        candidates = sorted(library_dir.glob("*/original.mp3"))
        rng = random.Random(args.seed)
        sample_size = min(args.sample, len(candidates))
        for original_path in rng.sample(candidates, k=sample_size):
            song_dir = original_path.parent
            add_job(song_dir.name, original_path, load_song_title(song_dir))

    return jobs


def gpu_cleanup() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


def status_callback(_msg: str) -> None:
    pass


def run_engine(
    engine_name: str,
    engine_fn: Callable[..., bool],
    input_path: Path,
    output_dir: Path,
) -> EngineRunResult:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stop_event = threading.Event()
    started = time.perf_counter()
    error: str | None = None
    success = False

    try:
        success = bool(
            engine_fn(
                input_path=input_path,
                song_dir=output_dir,
                status_callback=status_callback,
                stop_event=stop_event,
            )
        )
    except Exception as exc:
        error = str(exc)
        logger.error("%s failed for %s: %s", engine_name, input_path, exc, exc_info=True)
    finally:
        duration = round(time.perf_counter() - started, 2)
        gpu_cleanup()

    stems_present = {stem: (output_dir / stem).exists() for stem in STEM_FILES}
    if success and not all(stems_present.values()):
        success = False
        missing = [s for s, ok in stems_present.items() if not ok]
        error = error or f"Missing output stems: {', '.join(missing)}"

    return EngineRunResult(
        engine=engine_name,
        success=success,
        duration_seconds=duration,
        output_dir=str(output_dir),
        stems_present=stems_present,
        error=error,
    )


def copy_original(input_path: Path, dest: Path) -> bool:
    try:
        shutil.copy2(input_path, dest)
        return True
    except OSError as exc:
        logger.warning("Could not copy original to %s: %s", dest, exc)
        return False


def process_song(
    song_id: str,
    input_path: Path,
    title: str | None,
    output_root: Path,
) -> SongResult:
    song_out = output_root / song_id
    song_out.mkdir(parents=True, exist_ok=True)

    original_dest = song_out / "original.mp3"
    original_copied = copy_original(input_path, original_dest)

    engine_results: list[EngineRunResult] = []
    for engine_name, engine_fn in ENGINES:
        engine_dir = song_out / engine_name
        logger.info("Running %s on %s", engine_name, song_id)
        result = run_engine(engine_name, engine_fn, input_path, engine_dir)
        engine_results.append(result)
        status = "ok" if result.success else "FAILED"
        logger.info(
            "  %s: %s (%.1fs)",
            engine_name,
            status,
            result.duration_seconds,
        )

    return SongResult(
        song_id=song_id,
        title=title,
        input_path=str(input_path),
        original_copied=original_copied,
        engines=engine_results,
    )


def write_readme(output_root: Path) -> None:
    readme_path = output_root / "README.txt"
    readme_path.write_text(README_TEXT, encoding="utf-8")


def write_manifest(
    output_root: Path,
    songs: list[SongResult],
    args: argparse.Namespace,
) -> Path:
    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "library_dir": str(Path(args.library_dir).expanduser().resolve()),
        "sample": args.sample,
        "seed": args.seed if args.sample > 0 else None,
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "engines": [name for name, _ in ENGINES],
        "songs": [asdict(s) for s in songs],
    }
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def resolve_output_dir(arg: Path | None) -> Path:
    if arg is not None:
        return arg.expanduser().resolve()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return (REPO_ROOT / f"three_track_compare_{timestamp}").resolve()


def main() -> int:
    args = parse_args()
    jobs = collect_jobs(args)

    if not jobs:
        logger.error(
            "No songs to process. Use --song-id, --input, or --sample N with a populated library."
        )
        return 1

    output_root = resolve_output_dir(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    write_readme(output_root)

    logger.info("Output directory: %s", output_root)
    logger.info("Processing %d song(s)", len(jobs))
    if torch.cuda.is_available():
        logger.info("GPU: %s", torch.cuda.get_device_name(0))
    else:
        logger.warning("No CUDA GPU detected — separation will be very slow")

    song_results: list[SongResult] = []
    for song_id, input_path, title in jobs:
        label = f"{title} ({song_id})" if title else song_id
        logger.info("=== Song: %s ===", label)
        song_results.append(process_song(song_id, input_path, title, output_root))
        gpu_cleanup()

    manifest_path = write_manifest(output_root, song_results, args)

    total_runs = sum(len(s.engines) for s in song_results)
    successes = sum(1 for s in song_results for e in s.engines if e.success)
    logger.info("Done: %d/%d engine runs succeeded", successes, total_runs)
    logger.info("Manifest: %s", manifest_path)
    logger.info("Listen under: %s/<song_id>/{demucs_three_track,roformer_three_track}/", output_root)

    return 0 if successes == total_runs else 1


if __name__ == "__main__":
    raise SystemExit(main())
