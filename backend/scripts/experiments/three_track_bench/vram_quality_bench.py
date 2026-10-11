#!/usr/bin/env python3
"""Per-stage VRAM + quality benchmark for the three_track engine.

Each stage runs on a fixed input so variants are compared like-for-like:
  A. Demucs on original.mp3          (variants: seed repeat, other seed, segment, htdemucs)
  B. Roformer karaoke on A-baseline vocals (autocast / overlap / segment_size)
  C. De-noise on B-baseline backing   (autocast / overlap)

Quality metric: residual SNR in dB of variant vs the fp32 production-default
output (higher = closer; inf = identical). The "other seed" Demucs run gives
the run-to-run variation production already has today.
"""

import gc
import json
import logging
import random
import re
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

BACKEND = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND))

from audio_separator.separator import Separator  # noqa: E402
from demucs.api import Separator as DemucsSeparator  # noqa: E402

LIB = BACKEND.parent / "karaoke_library"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else None
SONGS = sys.argv[2].split(",") if len(sys.argv) > 2 else []

KARAOKE = "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt"
DENOISE = "denoise_mel_band_roformer_aufr33_sdr_27.9959.ckpt"
MDXC_DEFAULT = {
    "segment_size": 256,
    "override_model_segment_size": False,
    "batch_size": 1,
    "overlap": 8,
    "pitch_shift": 0,
}

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger("bench")
log.setLevel(logging.INFO)


def snr_db(ref: np.ndarray, x: np.ndarray) -> float:
    n = min(len(ref), len(x))
    ref, x = ref[:n].astype(np.float64), x[:n].astype(np.float64)
    err = np.sum((ref - x) ** 2)
    if err == 0:
        return float("inf")
    return float(10 * np.log10(np.sum(ref**2) / err))


def residual_peak_dbfs(ref: np.ndarray, x: np.ndarray) -> float:
    n = min(len(ref), len(x))
    peak = np.max(np.abs(ref[:n].astype(np.float64) - x[:n].astype(np.float64)))
    return float(20 * np.log10(peak)) if peak > 0 else float("-inf")


def free_gpu():
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()


def mb(b):
    return round(b / 2**20)


def run_demucs(src: Path, model: str, seed: int, segment=None):
    free_gpu()
    random.seed(seed)
    torch.manual_seed(seed)
    base = torch.cuda.memory_allocated()
    sep = DemucsSeparator(model=model, device="cuda", segment=segment)
    t0 = time.perf_counter()
    _, separated = sep.separate_audio_file(src)
    torch.cuda.synchronize()
    dt = time.perf_counter() - t0
    peak = torch.cuda.max_memory_allocated() - base
    peak_reserved = torch.cuda.max_memory_reserved()
    after = torch.cuda.memory_allocated() - base
    vocals = separated["vocals"].cpu().numpy().T
    instr = sum(v for k, v in separated.items() if k != "vocals").cpu().numpy().T
    sr = sep.samplerate
    del sep, separated
    return {
        "vocals": vocals,
        "instrumental": instr,
        "sr": sr,
        "seconds": round(dt, 2),
        "peak_alloc_mb": mb(peak),
        "peak_reserved_mb": mb(peak_reserved),
        "still_allocated_after_mb": mb(after),
    }


def run_roformer(src: Path, model: str, outdir: Path, autocast: bool, mdxc: dict):
    free_gpu()
    outdir.mkdir(parents=True, exist_ok=True)
    base = torch.cuda.memory_allocated()
    sep = Separator(
        output_dir=str(outdir),
        output_format="wav",
        use_autocast=autocast,
        mdxc_params=mdxc,
        log_level=logging.WARNING,
    )
    sep.load_model(model_filename=model)
    weights = torch.cuda.memory_allocated() - base
    torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    files = sep.separate(str(src))
    torch.cuda.synchronize()
    dt = time.perf_counter() - t0
    peak = torch.cuda.max_memory_allocated() - base
    peak_reserved = torch.cuda.max_memory_reserved()
    stems = {}
    for f in files:
        p = Path(f)
        if not p.is_absolute():
            p = outdir / p.name
        data, sr = sf.read(str(p), dtype="float32", always_2d=True)
        name = re.findall(r"\(([^)]+)\)", p.name)[-1]
        stems[name] = (data, sr, p)
    del sep
    return stems, {
        "seconds": round(dt, 2),
        "weights_mb": mb(weights),
        "peak_alloc_mb": mb(peak),
        "peak_reserved_mb": mb(peak_reserved),
        "nan": any(bool(np.isnan(d).any()) for d, _, _ in stems.values()),
    }


def compare(ref_stems, var_stems):
    out = {}
    for k, (ref, _, _) in ref_stems.items():
        if k in var_stems:
            x = var_stems[k][0]
            out[k] = {
                "snr_db": round(snr_db(ref, x), 1),
                "residual_peak_dbfs": round(residual_peak_dbfs(ref, x), 1),
            }
    return out


def bench_song(song_id: str):
    src = LIB / song_id / "original.mp3"
    title = json.load(open(LIB / song_id / "original.info.json")).get("title")
    sd = OUT / song_id
    sd.mkdir(parents=True, exist_ok=True)
    res = {"song_id": song_id, "title": title, "demucs": {}, "karaoke": {}, "denoise": {}}
    log.info("=== %s (%s)", title, song_id)

    # ---- A. Demucs
    base = run_demucs(src, "htdemucs_ft", seed=0)
    sr = base["sr"]
    voc_path = sd / "demucs_vocals.wav"
    sf.write(str(voc_path), base["vocals"], sr, subtype="PCM_16")  # same as prod
    sf.write(str(sd / "demucs_instrumental.wav"), base["instrumental"], sr, subtype="PCM_16")
    res["demucs"]["baseline_ft"] = {k: v for k, v in base.items() if k not in ("vocals", "instrumental", "sr")}

    variants = {
        "repeat_same_seed": ("htdemucs_ft", 0, None),
        "other_seed (prod run-to-run)": ("htdemucs_ft", 1, None),
        "segment_4": ("htdemucs_ft", 0, 4),
        "htdemucs_single": ("htdemucs", 0, None),
    }
    for name, (model, seed, seg) in variants.items():
        log.info("demucs %s", name)
        v = run_demucs(src, model, seed, seg)
        entry = {k: val for k, val in v.items() if k not in ("vocals", "instrumental", "sr")}
        entry["vocals_snr_db"] = round(snr_db(base["vocals"], v["vocals"]), 1)
        entry["instrumental_snr_db"] = round(snr_db(base["instrumental"], v["instrumental"]), 1)
        if name == "htdemucs_single":
            sf.write(str(sd / "demucs_instrumental_htdemucs.wav"), v["instrumental"], sr, subtype="PCM_16")
        res["demucs"][name] = entry
        del v
    del base

    # ---- B. Karaoke Roformer on fixed vocals
    kvariants = {
        "baseline_fp32_ov8": (False, {}),
        "repeat_fp32_ov8": (False, {}),
        "autocast_ov8": (True, {}),
        "fp32_ov4": (False, {"overlap": 4}),
        "fp32_ov2": (False, {"overlap": 2}),
        "autocast_ov4": (True, {"overlap": 4}),
        "autocast_ov8_seg401": (True, {"segment_size": 401, "override_model_segment_size": True}),
        "autocast_ov8_seg256": (True, {"segment_size": 256, "override_model_segment_size": True}),
    }
    kref = None
    for name, (ac, over) in kvariants.items():
        log.info("karaoke %s", name)
        stems, stats = run_roformer(voc_path, KARAOKE, sd / f"karaoke_{name}", ac, {**MDXC_DEFAULT, **over})
        if kref is None:
            kref = stems
        else:
            stats["vs_baseline"] = compare(kref, stems)
        res["karaoke"][name] = stats
    backing_path = next(p for k, (_, _, p) in kref.items() if k.lower() == "instrumental")

    # ---- C. De-noise on fixed backing
    dvariants = {
        "baseline_fp32_ov8": (False, {}),
        "autocast_ov8": (True, {}),
        "fp32_ov4": (False, {"overlap": 4}),
        "autocast_ov4": (True, {"overlap": 4}),
    }
    dref = None
    for name, (ac, over) in dvariants.items():
        log.info("denoise %s", name)
        stems, stats = run_roformer(backing_path, DENOISE, sd / f"denoise_{name}", ac, {**MDXC_DEFAULT, **over})
        if dref is None:
            dref = stems
        else:
            stats["vs_baseline"] = compare(dref, stems)
        res["denoise"][name] = stats
    # how much does de-noise change the backing at all?
    raw, _ = sf.read(str(backing_path), dtype="float32", always_2d=True)
    dry = next(d for k, (d, _, _) in dref.items() if k.lower() == "dry")
    res["denoise"]["dry_vs_raw_backing_snr_db"] = round(snr_db(raw, dry), 1)

    (sd / "results.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    log.info("GPU: %s", torch.cuda.get_device_name(0))
    free, total = torch.cuda.mem_get_info()
    log.info("free %d MB / total %d MB before start", mb(free), mb(total))
    allres = []
    for s in SONGS:
        allres.append(bench_song(s))
        (OUT / "all_results.json").write_text(json.dumps(allres, indent=1))
    log.info("done")
