#!/usr/bin/env python3
"""Follow-up to vram_quality_bench.py.

1. Seam test: does today's karaoke output (overlap=8 -> step 8s == chunk 8s,
   i.e. no overlap) show discontinuities at the 8s chunk boundaries?
   - jump ratio: median |x[t]-x[t-1]| at boundary samples / same stat at
     random non-boundary samples (1.0 = no seam)
   - residual-vs-corrected concentration: energy of (today - corrected)
     within +-25ms of boundaries vs elsewhere
2. Proposed config: autocast + overlap=2 (== upstream num_overlap=4 fix) on
   karaoke and denoise, compared to fp32 overlap=2 and timed.
"""

import json
import logging
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
import vram_quality_bench as b  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else None
SR = 44100
CHUNK = 441 * 800  # 352800 samples = 8.0 s (dim_t 801)


def stem(dirpath: Path, name: str) -> np.ndarray:
    f = next(p for p in dirpath.glob("*.wav") if f"({name})" in p.name)
    return sf.read(str(f), dtype="float64", always_2d=True)[0]


def seam_stats(today: np.ndarray, fixed: np.ndarray) -> dict:
    n = min(len(today), len(fixed))
    today, fixed = today[:n], fixed[:n]
    bounds = np.arange(CHUNK, n - CHUNK, CHUNK)  # last chunk is tail-aligned, skip
    if len(bounds) == 0:
        return {}
    jump = np.abs(np.diff(today, axis=0)).mean(axis=1)
    rng = np.random.default_rng(0)
    rand = rng.integers(SR, n - SR, 5000)
    jump_ratio = float(np.median(jump[bounds - 1]) / np.median(jump[rand]))
    jump_fixed = np.abs(np.diff(fixed, axis=0)).mean(axis=1)
    jump_ratio_fixed = float(np.median(jump_fixed[bounds - 1]) / np.median(jump_fixed[rand]))

    res = ((today - fixed) ** 2).mean(axis=1)
    w = int(0.025 * SR)
    mask = np.zeros(n, bool)
    for bd in bounds:
        mask[bd - w : bd + w] = True
    conc = float(res[mask].mean() / res[~mask].mean())
    return {
        "boundaries": int(len(bounds)),
        "jump_ratio_today": round(jump_ratio, 2),
        "jump_ratio_corrected": round(jump_ratio_fixed, 2),
        "residual_energy_at_boundaries_x": round(conc, 1),
    }


def main():
    results = []
    for sd in sorted(p for p in OUT.iterdir() if p.is_dir()):
        r = json.loads((sd / "results.json").read_text())
        entry = {"title": r["title"], "seams": {}, "proposed": {}}
        for nm in ("Vocals", "Instrumental"):
            entry["seams"][nm] = seam_stats(
                stem(sd / "karaoke_baseline_fp32_ov8", nm), stem(sd / "karaoke_fp32_ov2", nm)
            )
        # also the corrected-vs-corrected control (ov4 vs ov2): should be uniform
        entry["seams"]["control_ov4_vs_ov2_Instrumental"] = seam_stats(
            stem(sd / "karaoke_fp32_ov4", "Instrumental"), stem(sd / "karaoke_fp32_ov2", "Instrumental")
        )

        voc = sd / "demucs_vocals.wav"
        kref, _ = b.run_roformer(voc, b.KARAOKE, sd / "karaoke_fp32_ov2_ref", False, {**b.MDXC_DEFAULT, "overlap": 2})
        kst, kstats = b.run_roformer(voc, b.KARAOKE, sd / "karaoke_autocast_ov2", True, {**b.MDXC_DEFAULT, "overlap": 2})
        kstats["vs_fp32_ov2"] = b.compare(kref, kst)
        entry["proposed"]["karaoke_autocast_ov2"] = kstats

        backing = next(p for p in (sd / "karaoke_fp32_ov2_ref").glob("*.wav") if "(Instrumental)" in p.name)
        dref, dstats_ref = b.run_roformer(backing, b.DENOISE, sd / "denoise_fp32_ov2", False, {**b.MDXC_DEFAULT, "overlap": 2})
        dst, dstats = b.run_roformer(backing, b.DENOISE, sd / "denoise_autocast_ov2", True, {**b.MDXC_DEFAULT, "overlap": 2})
        dstats["vs_fp32_ov2"] = b.compare(dref, dst)
        entry["proposed"]["denoise_fp32_ov2_seconds"] = dstats_ref["seconds"]
        entry["proposed"]["denoise_autocast_ov2"] = dstats
        results.append(entry)
        b.log.info("%s: %s", r["title"], json.dumps(entry["seams"]))
    (OUT / "seam_and_proposed.json").write_text(json.dumps(results, indent=1))
    b.log.info("done")


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.WARNING)
    main()
