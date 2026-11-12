#!/usr/bin/env python3
"""audio-separator 0.47.0 (shadowed via PYTHONPATH) on the same fixed inputs.

Compares against the 0.30.2 overlap=2 outputs written by seam_and_proposed.py
(karaoke_fp32_ov2_ref / denoise_fp32_ov2), which use the identical 2 s step.
"""

import gc
import json
import logging
import sys
import time
from pathlib import Path

import audio_separator
import numpy as np
import soundfile as sf
import torch
from audio_separator.separator import Separator

sys.path.insert(0, str(Path(__file__).parent))
import vram_quality_bench as b  # noqa: E402

assert "as047" in audio_separator.__file__, audio_separator.__file__
OUT = Path(sys.argv[1])

VARIANTS = {
    "047_fp32": {},
    "047_autocast": {"use_autocast": True},
    "047_native_fp16": {"use_native_fp16": True},
}


def run(src: Path, model: str, outdir: Path, **kw):
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    outdir.mkdir(parents=True, exist_ok=True)
    base = torch.cuda.memory_allocated()
    sep = Separator(output_dir=str(outdir), output_format="wav", log_level=logging.WARNING, **kw)
    sep.load_model(model_filename=model)
    weights = torch.cuda.memory_allocated() - base
    torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    files = sep.separate(str(src))
    torch.cuda.synchronize()
    dt = time.perf_counter() - t0
    peak = torch.cuda.max_memory_allocated() - base
    stems = {}
    for f in files:
        p = Path(f)
        if not p.is_absolute():
            p = outdir / p.name
        data, sr = sf.read(str(p), dtype="float32", always_2d=True)
        stems[b.re.findall(r"\(([^)]+)\)", p.name)[-1]] = (data, sr, p)
    del sep
    return stems, {
        "seconds": round(dt, 2),
        "weights_mb": b.mb(weights),
        "peak_alloc_mb": b.mb(peak),
        "nan": any(bool(np.isnan(d).any()) for d, _, _ in stems.values()),
    }


def load_dir(d: Path):
    out = {}
    for p in d.glob("*.wav"):
        data, sr = sf.read(str(p), dtype="float32", always_2d=True)
        out[b.re.findall(r"\(([^)]+)\)", p.name)[-1]] = (data, sr, p)
    return out


def main():
    allres = []
    for sd in sorted(p for p in OUT.iterdir() if p.is_dir()):
        title = json.loads((sd / "results.json").read_text())["title"]
        kref = load_dir(sd / "karaoke_fp32_ov2_ref")
        dref = load_dir(sd / "denoise_fp32_ov2")
        backing_in = next(p for _, (_, _, p) in kref.items() if "(Instrumental)" in p.name)
        res = {"title": title, "karaoke": {}, "denoise": {}}
        for name, kw in VARIANTS.items():
            b.log.info("%s karaoke %s", title, name)
            st, stats = run(sd / "demucs_vocals.wav", b.KARAOKE, sd / f"karaoke_{name}", **kw)
            stats["vs_030_ov2_fp32"] = b.compare(kref, st)
            res["karaoke"][name] = stats
            b.log.info("%s denoise %s", title, name)
            st, stats = run(backing_in, b.DENOISE, sd / f"denoise_{name}", **kw)
            stats["vs_030_ov2_fp32"] = b.compare(dref, st)
            res["denoise"][name] = stats
        allres.append(res)
        (OUT / "bench047.json").write_text(json.dumps(allres, indent=1))
    b.log.info("done")


if __name__ == "__main__":
    main()
