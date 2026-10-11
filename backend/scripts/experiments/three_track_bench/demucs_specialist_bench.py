#!/usr/bin/env python3
"""htdemucs_ft bag vs its vocals specialist alone, on original.mp3.

The bag runs four HTDemucs models with one-hot weights; only model 3's vocals
are kept from it. Running model 3 alone gives the same vocals stem (the
Roformer input) at a quarter of the work. The instrumental then has to come
from somewhere else:

  specialist_mix_minus  instrumental = mix - specialist vocals
  specialist_own_stems  instrumental = specialist's drums + bass + other

Reference is today's bag at seed 0; "other_seed" is today's run-to-run spread.
Writes each instrumental (and vocals) as WAV for listening.

    demucs_specialist_bench.py <out_dir> <song_id>,<song_id>,...
"""

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

VOCALS_SPECIALIST = 3


def separate(src: Path, seed: int, specialist: bool):
    b.free_gpu()
    random.seed(seed)
    torch.manual_seed(seed)
    sep = DemucsSeparator(model="htdemucs_ft", device="cuda")
    if specialist:
        bag = sep._model
        assert bag.weights[VOCALS_SPECIALIST] == [0.0, 0.0, 0.0, 1.0], bag.weights
        sep._model = bag.models[VOCALS_SPECIALIST]
    t0 = time.perf_counter()
    mix, stems = sep.separate_audio_file(src)
    torch.cuda.synchronize()
    seconds = round(time.perf_counter() - t0, 2)
    peak = b.mb(torch.cuda.max_memory_allocated())
    out = {k: v.cpu().numpy().T for k, v in stems.items()}
    return mix.cpu().numpy().T, out, sep.samplerate, seconds, peak


def bench_song(out: Path, song_id: str):
    src = b.LIB / song_id / "original.mp3"
    title = json.load(open(b.LIB / song_id / "original.info.json")).get("title")
    sd = out / song_id
    sd.mkdir(parents=True, exist_ok=True)
    b.log.info("=== %s", title)

    def instr_sum(stems):
        return sum(v for k, v in stems.items() if k != "vocals")

    def save(name, audio, sr):
        sf.write(str(sd / f"{name}.wav"), audio, sr, subtype="PCM_16")

    _, ref, sr, ref_s, ref_peak = separate(src, 0, specialist=False)
    ref_instr = instr_sum(ref)
    save("today_instrumental", ref_instr, sr)
    save("today_vocals", ref["vocals"], sr)
    res = {"title": title, "today": {"seconds": ref_s, "peak_alloc_mb": ref_peak}}

    def score(vocals, instr):
        return {
            "vocals_snr_db": round(b.snr_db(ref["vocals"], vocals), 1),
            "instrumental_snr_db": round(b.snr_db(ref_instr, instr), 1),
        }

    _, other, _, s, peak = separate(src, 1, specialist=False)
    res["other_seed"] = {
        "seconds": s,
        "peak_alloc_mb": peak,
        **score(other["vocals"], instr_sum(other)),
    }
    save("other_seed_instrumental", instr_sum(other), sr)
    del other

    mix, spec, _, s, peak = separate(src, 0, specialist=True)
    minus = mix - spec["vocals"]
    own = instr_sum(spec)
    save("specialist_vocals", spec["vocals"], sr)
    save("specialist_mix_minus_instrumental", minus, sr)
    save("specialist_own_stems_instrumental", own, sr)
    res["specialist_mix_minus"] = {
        "seconds": s,
        "peak_alloc_mb": peak,
        **score(spec["vocals"], minus),
    }
    res["specialist_own_stems"] = {
        "seconds": s,
        "peak_alloc_mb": peak,
        **score(spec["vocals"], own),
    }
    return res


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    allres = [bench_song(out, s) for s in sys.argv[2].split(",")]
    (out / "demucs_specialist.json").write_text(json.dumps(allres, indent=1))
    print(json.dumps(allres, indent=1))
