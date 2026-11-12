#!/usr/bin/env python3
"""Where the engine's wall time goes outside model inference.

Runs the real engine with timers wrapped around model loads, audio decode,
inference, WAV writes and GPU release. The first run warms up torch.compile and
the OS file cache; the breakdown is from later runs (best of --runs per song).

    overhead_breakdown.py <out_dir> <song_id>,<song_id> [--runs N]
"""

import functools
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import torch
from audio_separator.separator.architectures.mdxc_separator import MDXCSeparator
from audio_separator.separator.common_separator import CommonSeparator
from demucs.api import Separator as DemucsSeparator

BACKEND = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND))

from app.services.separation_engines import three_track  # noqa: E402

times: dict = defaultdict(float)
roformer_pass = {"n": 0}


def timed(key_fn, fn, sync=False):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        key = key_fn(*args, **kwargs)
        t0 = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            if sync:
                torch.cuda.synchronize()
            times[key] += time.perf_counter() - t0

    return wrapper


def pass_name(*_a, **_k):
    return ("karaoke", "denoise")[roformer_pass["n"] % 2]


def patch():
    three_track.DemucsSeparator = timed(lambda **k: "demucs_load", DemucsSeparator)
    DemucsSeparator._load_audio = timed(
        lambda *a: "demucs_decode", DemucsSeparator._load_audio
    )
    DemucsSeparator.separate_tensor = timed(
        lambda *a, **k: "demucs_infer", DemucsSeparator.separate_tensor, sync=True
    )
    # Only the engine's own writes; audio-separator imports soundfile too
    sf = three_track.sf
    three_track.sf = SimpleNamespace(
        write=timed(lambda *a, **k: "demucs_wav_write", sf.write)
    )
    three_track.release_gpu_memory = timed(
        lambda: "release_gpu", three_track.release_gpu_memory
    )
    load = three_track.load_separator
    three_track.load_separator = timed(lambda m, *a, **k: f"{_short(m)}_load", load)
    MDXCSeparator.prepare_mix = timed(
        lambda *a: f"{pass_name()}_read", MDXCSeparator.prepare_mix
    )
    MDXCSeparator.demix = timed(
        lambda *a, **k: f"{pass_name()}_infer", MDXCSeparator.demix, sync=True
    )
    CommonSeparator.write_audio = timed(
        lambda *a: f"{pass_name()}_wav_write", CommonSeparator.write_audio
    )
    sep = MDXCSeparator.separate

    def separate(self, *a, **k):
        try:
            return sep(self, *a, **k)
        finally:
            roformer_pass["n"] += 1

    MDXCSeparator.separate = timed(lambda *a, **k: f"{pass_name()}_separate", separate)
    three_track._export_mp3 = timed(
        lambda *a: "mp3_export_cpu", three_track._export_mp3
    )


def _short(model: str) -> str:
    return "denoise" if model == three_track.DENOISE_MODEL else "karaoke"


def run(out: Path, song_id: str, n: int) -> dict:
    times.clear()
    roformer_pass["n"] = 0
    song_dir = out / f"{song_id}_{n}"
    song_dir.mkdir(parents=True, exist_ok=True)
    timing: dict = {}
    t0 = time.perf_counter()
    ok = three_track.separate_with_three_track(
        BACKEND.parent / "karaoke_library" / song_id / "original.mp3",
        song_dir,
        status_callback=lambda m: None,
        timing_sink=timing,
    )
    stages = {
        s: round(timing[f"{s}_end"] - timing[f"{s}_start"], 2)
        for s in ("demucs", "roformer", "denoise", "mp3_conversion")
    }
    return {
        "song_id": song_id,
        "success": ok,
        "seconds": round(time.perf_counter() - t0, 2),
        "stages_s": stages,
        "parts_s": {k: round(v, 2) for k, v in sorted(times.items())},
    }


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    runs = 2
    if "--runs" in sys.argv:
        runs = int(sys.argv[sys.argv.index("--runs") + 1])
        args.remove(str(runs))
    out = Path(args[0])
    out.mkdir(parents=True, exist_ok=True)
    patch()
    songs = args[1].split(",")
    run(out, songs[0], 0)  # warm-up
    best = {}
    for i in range(runs):
        for song_id in songs:
            r = run(out, song_id, i + 1)
            print(json.dumps(r), flush=True)
            if song_id not in best or r["seconds"] < best[song_id]["seconds"]:
                best[song_id] = r
    (out / "overhead_breakdown.json").write_text(json.dumps(best, indent=1))
