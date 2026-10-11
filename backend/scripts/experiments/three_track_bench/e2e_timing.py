#!/usr/bin/env python3
"""Whole-engine time per song, current code vs MP3 exports run inline.

"inline" swaps the engine's MP3 encoder pool for one that runs each export
when it's submitted, which puts every export back on the critical path (the
engine before background exports). Runs alternate modes in one process, after
one warm-up run (torch.compile), so both see the same GPU conditions.

    e2e_timing.py <out_dir> <song_id>,<song_id> [--runs N]
"""

import json
import sys
import time
from concurrent.futures import Future
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND))

from app.services.separation_engines import three_track  # noqa: E402

STAGES = ("demucs", "roformer", "denoise", "mp3_conversion")


class InlineExecutor:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def submit(self, fn, *args):
        f: Future = Future()
        try:
            f.set_result(fn(*args))
        except Exception as e:
            f.set_exception(e)
        return f


def run(out: Path, song_id: str, mode: str, n: int) -> dict:
    three_track.ThreadPoolExecutor = (
        InlineExecutor if mode == "inline" else POOL_EXECUTOR
    )
    song_dir = out / f"{song_id}_{mode}_{n}"
    song_dir.mkdir(parents=True, exist_ok=True)
    timing: dict = {}
    vocals_at = []
    t0 = time.perf_counter()
    ok = three_track.separate_with_three_track(
        BACKEND.parent / "karaoke_library" / song_id / "original.mp3",
        song_dir,
        status_callback=lambda m: None,
        timing_sink=timing,
        on_vocals_ready=lambda p: vocals_at.append(time.perf_counter() - t0),
    )
    return {
        "mode": mode,
        "success": ok,
        "seconds": round(time.perf_counter() - t0, 1),
        "vocals_ready_s": round(vocals_at[0], 1) if vocals_at else None,
        "stages_s": {
            s: round(timing[f"{s}_end"] - timing[f"{s}_start"], 1)
            for s in STAGES
            if f"{s}_end" in timing
        },
    }


POOL_EXECUTOR = three_track.ThreadPoolExecutor

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    runs = 2
    if "--runs" in sys.argv:
        runs = int(sys.argv[sys.argv.index("--runs") + 1])
        args.remove(str(runs))
    out = Path(args[0])
    out.mkdir(parents=True, exist_ok=True)
    songs = args[1].split(",")
    run(out, songs[0], "pool", 0)  # warm-up: compile
    results = []
    for i in range(runs):
        for song_id in songs:
            for mode in ("inline", "pool") if i % 2 == 0 else ("pool", "inline"):
                r = {"song_id": song_id, **run(out, song_id, mode, i + 1)}
                print(json.dumps(r), flush=True)
                results.append(r)
    (out / "e2e_timing.json").write_text(json.dumps(results, indent=1))
