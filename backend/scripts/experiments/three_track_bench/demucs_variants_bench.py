#!/usr/bin/env python3
"""Demucs vocals model (the engine's step 1) under inference variants.

Each variant runs on original.mp3 with the same seed as the baseline, so the
random shift is identical and the diff isolates the variant:

  baseline         fp32, overlap 0.25 (today)
  other_seed       baseline at seed 1: today's run-to-run spread
  autocast         torch.autocast fp16 around inference
  overlap_<x>      split overlap x instead of 0.25
  gpu_mix          mix tensor on the GPU, so Demucs's overlap-add buffer is too
                   (given a CPU tensor, it accumulates every chunk on the CPU)

Join variants with "+" to combine them, e.g. autocast+gpu_mix.

Audio is decoded once; times are inference only (separate_tensor), best of
--repeats after one warm-up. Writes vocals, instrumental (mix - vocals) and
the diff against baseline for each variant as WAV, for listening.

    demucs_variants_bench.py <out_dir> <song_id>,<song_id> [variant,...] [--repeats N]

Variants: autocast, overlap_0.1, overlap_0 ... (default: autocast)
"""

import contextlib
import json
import random
import sys
import time
from pathlib import Path

import soundfile as sf
import torch
from demucs.api import Separator as DemucsSeparator

sys.path.insert(0, str(Path(__file__).parent))
import vram_quality_bench as b  # noqa: E402

BACKEND = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND))
from app.services.separation_engines.three_track import (  # noqa: E402
    _use_vocals_specialist,
)


def parse_variant(name: str) -> dict:
    kw: dict = {}
    if name in ("baseline", "other_seed"):
        return kw
    for part in name.split("+"):
        if part == "autocast":
            kw["autocast"] = True
        elif part == "gpu_mix":
            kw["gpu_mix"] = True
        elif part.startswith("overlap_"):
            kw["overlap"] = float(part.removeprefix("overlap_"))
        else:
            raise SystemExit(f"unknown variant {part}")
    return kw


def make_separator() -> DemucsSeparator:
    sep = DemucsSeparator(model="htdemucs_ft", device="cuda")
    assert _use_vocals_specialist(sep)
    return sep


def run(sep, wav, seed: int, autocast=False, overlap=0.25, gpu_mix=False):
    """One inference; returns (vocals, instrumental) as numpy, seconds, peak MB."""
    sep.update_parameter(overlap=overlap)
    b.free_gpu()
    if gpu_mix:
        wav = wav.cuda()
    random.seed(seed)
    torch.manual_seed(seed)
    ctx = (
        torch.autocast("cuda", dtype=torch.float16)
        if autocast
        else contextlib.nullcontext()
    )
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    with ctx:
        mix, stems = sep.separate_tensor(wav)
    torch.cuda.synchronize()
    seconds = time.perf_counter() - t0
    peak = b.mb(torch.cuda.max_memory_allocated())
    vocals = stems["vocals"].float().cpu()
    instr = mix.cpu() - vocals
    del mix, stems
    return vocals.numpy().T, instr.numpy().T, seconds, peak


def bench_song(out: Path, song_id: str, variants: list[str], repeats: int):
    src = b.LIB / song_id / "original.mp3"
    title = json.load(open(b.LIB / song_id / "original.info.json")).get("title")
    sd = out / song_id
    sd.mkdir(parents=True, exist_ok=True)
    b.log.info("=== %s", title)

    sep = make_separator()
    wav = sep._load_audio(src)  # decoded once, same tensor for every run
    sr = sep.samplerate

    def save(name, audio):
        sf.write(str(sd / f"{name}.wav"), audio, sr, subtype="FLOAT")

    def timed(seed, **kw):
        best, result = None, None
        for _ in range(repeats + 1):  # first run is warm-up
            v, i, s, peak = run(sep, wav, seed, **kw)
            if result is not None:
                best = s if best is None else min(best, s)
            result = (v, i, peak)
        return (*result, round(best, 2))

    ref_v, ref_i, ref_peak, ref_s = timed(0)
    save("baseline_vocals", ref_v)
    save("baseline_instrumental", ref_i)
    res = {"title": title, "baseline": {"seconds": ref_s, "peak_alloc_mb": ref_peak}}

    def score(v, i):
        return {
            "vocals_snr_db": round(b.snr_db(ref_v, v), 1),
            "instrumental_snr_db": round(b.snr_db(ref_i, i), 1),
            "nan": bool(torch.isnan(torch.from_numpy(v)).any()),
        }

    for name in ["other_seed", *variants]:
        seed = 1 if name == "other_seed" else 0
        v, i, peak, s = timed(seed, **parse_variant(name))
        res[name] = {"seconds": s, "peak_alloc_mb": peak, **score(v, i)}
        save(f"{name}_vocals", v)
        save(f"{name}_instrumental", i)
        save(f"{name}_vocals_diff", v - ref_v)
        save(f"{name}_instrumental_diff", i - ref_i)
        b.log.info("%s: %s", name, res[name])
    del sep
    b.free_gpu()
    return res


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    repeats = 3
    if "--repeats" in sys.argv:
        repeats = int(sys.argv[sys.argv.index("--repeats") + 1])
        args.remove(str(repeats))
    out = Path(args[0])
    out.mkdir(parents=True, exist_ok=True)
    variants = args[2].split(",") if len(args) > 2 else ["autocast"]
    allres = [bench_song(out, s, variants, repeats) for s in args[1].split(",")]
    (out / "demucs_variants.json").write_text(json.dumps(allres, indent=1))
    print(json.dumps(allres, indent=1))
