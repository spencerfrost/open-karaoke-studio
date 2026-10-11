#!/usr/bin/env python3
"""Run the real three_track engine, unmodified, under a VRAM cap.

Usage: e2e_capped.py <out_dir> <song_id> <cap_gb>
"""

import json
import sys
import time
from pathlib import Path

import torch

BACKEND = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND))

from app.services.separation_engines.three_track import separate_with_three_track  # noqa: E402

out, song_id, cap_gb = Path(sys.argv[1]), sys.argv[2], float(sys.argv[3])
total = torch.cuda.get_device_properties(0).total_memory
torch.cuda.set_per_process_memory_fraction(cap_gb * 2**30 / total)
torch.cuda.reset_peak_memory_stats()

song_dir = out / f"e2e_{song_id}_{cap_gb}gb"
song_dir.mkdir(parents=True, exist_ok=True)
timing: dict = {}
t0 = time.perf_counter()
err = None
try:
    ok = separate_with_three_track(
        BACKEND.parent / "karaoke_library" / song_id / "original.mp3",
        song_dir,
        status_callback=lambda m: None,
        timing_sink=timing,
    )
except Exception as e:  # OOM is re-raised by the engine
    ok, err = False, repr(e)[:300]
res = {
    "song_id": song_id,
    "cap_gb": cap_gb,
    "success": ok,
    "error": err,
    "seconds": round(time.perf_counter() - t0, 1),
    "peak_alloc_mb": round(torch.cuda.max_memory_allocated() / 2**20),
    "peak_reserved_mb": round(torch.cuda.max_memory_reserved() / 2**20),
    "stages_s": {
        s: round(timing[f"{s}_end"] - timing[f"{s}_start"], 1)
        for s in ("demucs", "roformer", "denoise", "mp3_conversion")
        if f"{s}_end" in timing
    },
}
print(json.dumps(res))
(song_dir / "e2e.json").write_text(json.dumps(res, indent=1))
