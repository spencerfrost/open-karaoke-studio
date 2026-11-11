"""Compute and cache a pitch contour per test song, once per setting.

Range methods (methods.py) read these caches, so pyin runs once per song per
setting however many methods are tried. Resumable: songs already cached are
skipped. Runs in parallel processes at low CPU priority.

Usage (from backend/, venv active):
    python scripts/experiments/vocal_range/extract.py [--setting pyin] [--jobs 8]
    python scripts/experiments/vocal_range/extract.py --list
"""

from __future__ import annotations

import argparse
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Callable

import numpy as np
from common import contour_path, load_testset

# Each setting: name -> function(vocals_path) -> dict of arrays for the npz.


def _pyin(sample_rate: int, fmin: str, fmax: str, hop_length: int = 512) -> Callable:
    def run(vocals_path: str) -> dict:
        import librosa

        y, sr = librosa.load(vocals_path, sr=sample_rate, mono=True)
        f0, voiced_flag, voiced_prob = librosa.pyin(
            y,
            fmin=librosa.note_to_hz(fmin),
            fmax=librosa.note_to_hz(fmax),
            sr=sr,
            hop_length=hop_length,
        )
        times = librosa.times_like(f0, sr=sr, hop_length=hop_length)
        return {
            "times": times.astype(np.float32),
            "f0": f0.astype(np.float32),
            "voiced_flag": voiced_flag,
            "voiced_prob": voiced_prob.astype(np.float32),
            "hop_seconds": np.float32(hop_length / sr),
        }

    return run


SETTINGS: dict[str, Callable] = {
    # Exactly what vocal_range_child.py runs today.
    "pyin": _pyin(22050, "C2", "C7"),
    # The same with fmax at C6: above any pop lead outside whistle notes.
    "pyin-c6": _pyin(22050, "C2", "C6"),
}


def _extract_one(setting: str, song_id: str, vocals_path: str) -> tuple[str, float]:
    os.nice(10)
    started = time.monotonic()
    arrays = SETTINGS[setting](vocals_path)
    path = contour_path(setting, song_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, **arrays)
    tmp.rename(path)
    return song_id, time.monotonic() - started


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--setting", default="pyin")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        print("\n".join(SETTINGS))
        return
    if args.setting not in SETTINGS:
        raise SystemExit(f"Unknown setting {args.setting!r}; --list shows them")

    todo = [
        s
        for s in load_testset()
        if not contour_path(args.setting, s["song_id"]).exists()
    ]
    print(f"{args.setting}: {len(todo)} songs to extract")
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = {
            pool.submit(_extract_one, args.setting, s["song_id"], s["vocals_path"]): s
            for s in todo
        }
        for done, future in enumerate(as_completed(futures), 1):
            song = futures[future]
            try:
                _, seconds = future.result()
                print(
                    f"[{done}/{len(todo)}] {seconds:5.1f}s  {song['artist']} - {song['title']}"
                )
            except Exception as e:  # one bad file shouldn't stop the run
                print(f"[{done}/{len(todo)}] FAILED {song['song_id']}: {e}")


if __name__ == "__main__":
    main()
