#!/usr/bin/env python3
"""Compare audio-separator versions on the Roformer passes, on fixed inputs.

    version_bench.py prepare <out_dir> <song_id>,<song_id>,...
        Demucs (seed 0) -> demucs_vocals.wav, then today's output as the reference:
        0.30.2 fp32 karaoke on those vocals, and 0.30.2 fp32 de-noise on its backing.
        Run with the venv's audio-separator (0.30.2).

    PYTHONPATH=<unpacked wheel> version_bench.py run <out_dir>
        Runs the variants for whichever audio-separator is importable on the same
        inputs and compares each stem against the reference.

Every variant keeps today's chunking: one pass per 8 s chunk, no overlap.
On 0.30.2/0.44.5 that is the default (overlap is a step in seconds, clamped to
the chunk); on 0.47.0 it is overlap=1 (a window count).
Times: load = model load, sep1 = first separate (includes torch.compile warm-up),
sep2 = a second separate on the same instance.
"""

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
from packaging.version import Version

sys.path.insert(0, str(Path(__file__).parent))
import vram_quality_bench as b  # noqa: E402


def version_from_path() -> str:
    """Unpacked wheels live in a dir with the matching dist-info."""
    root = Path(audio_separator.__file__).parents[1]
    info = next(root.glob("audio_separator-*.dist-info"), None)
    if info is not None:
        return info.name.removeprefix("audio_separator-").removesuffix(".dist-info")
    from importlib.metadata import version

    return version("audio-separator")


VERSION = Version(version_from_path())
ONE_PASS_047 = {
    "segment_size": 256,
    "override_model_segment_size": False,
    "batch_size": None,
    "overlap": 1,
    "pitch_shift": 0,
}


def variants() -> dict:
    if VERSION >= Version("0.47.0"):
        return {
            "fp32": {"mdxc_params": ONE_PASS_047},
            "autocast": {"mdxc_params": ONE_PASS_047, "use_autocast": True},
            "autocast_compile": {
                "mdxc_params": ONE_PASS_047,
                "use_autocast": True,
                "use_torch_compile": True,
            },
        }
    return {"fp32": {}, "autocast": {"use_autocast": True}}


def run(src: Path, model: str, outdir: Path, kw: dict, repeat: bool):
    b.free_gpu()
    outdir.mkdir(parents=True, exist_ok=True)
    base = torch.cuda.memory_allocated()
    t0 = time.perf_counter()
    sep = Separator(
        output_dir=str(outdir), output_format="wav", log_level=logging.WARNING, **kw
    )
    sep.load_model(model_filename=model)
    torch.cuda.synchronize()
    load_s = time.perf_counter() - t0
    torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    files = sep.separate(str(src))
    torch.cuda.synchronize()
    sep1 = time.perf_counter() - t0
    stats = {"load_s": round(load_s, 2), "sep1_s": round(sep1, 2)}
    if repeat:
        t0 = time.perf_counter()
        sep.separate(str(src))
        torch.cuda.synchronize()
        stats["sep2_s"] = round(time.perf_counter() - t0, 2)
    stats["peak_alloc_mb"] = b.mb(torch.cuda.max_memory_allocated() - base)
    stems = {}
    for f in files:
        p = Path(f)
        if not p.is_absolute():
            p = outdir / p.name
        data, sr = sf.read(str(p), dtype="float32", always_2d=True)
        stems[b.re.findall(r"\(([^)]+)\)", p.name)[-1]] = (data, sr, p)
    stats["nan"] = any(bool(np.isnan(d).any()) for d, _, _ in stems.values())
    del sep
    return stems, stats


def load_dir(d: Path):
    out = {}
    for p in d.glob("*.wav"):
        data, sr = sf.read(str(p), dtype="float32", always_2d=True)
        out[b.re.findall(r"\(([^)]+)\)", p.name)[-1]] = (data, sr, p)
    return out


def backing_of(stems: dict) -> Path:
    return next(p for k, (_, _, p) in stems.items() if k.lower() == "instrumental")


def prepare(out: Path, songs: list[str]):
    assert VERSION == Version("0.30.2"), VERSION
    for song_id in songs:
        sd = out / song_id
        sd.mkdir(parents=True, exist_ok=True)
        src = b.LIB / song_id / "original.mp3"
        title = json.load(open(b.LIB / song_id / "original.info.json")).get("title")
        b.log.info("prepare %s", title)
        d = b.run_demucs(src, "htdemucs_ft", seed=0)
        sf.write(str(sd / "demucs_vocals.wav"), d["vocals"], d["sr"], subtype="PCM_16")
        kref, _ = run(
            sd / "demucs_vocals.wav", b.KARAOKE, sd / "ref_karaoke", {}, False
        )
        run(backing_of(kref), b.DENOISE, sd / "ref_denoise", {}, False)
        (sd / "song.json").write_text(json.dumps({"title": title}))


def bench(out: Path):
    label = str(VERSION)
    results = {}
    for sd in sorted(p for p in out.iterdir() if (p / "song.json").exists()):
        title = json.loads((sd / "song.json").read_text())["title"]
        kref = load_dir(sd / "ref_karaoke")
        dref = load_dir(sd / "ref_denoise")
        res = {"karaoke": {}, "denoise": {}}
        for name, kw in variants().items():
            repeat = "compile" in name
            b.log.info("%s %s karaoke %s", label, title, name)
            st, stats = run(
                sd / "demucs_vocals.wav",
                b.KARAOKE,
                sd / f"{label}_karaoke_{name}",
                kw,
                repeat,
            )
            stats["vs_today"] = b.compare(kref, st)
            res["karaoke"][name] = stats
            b.log.info("%s %s denoise %s", label, title, name)
            st, stats = run(
                backing_of(kref), b.DENOISE, sd / f"{label}_denoise_{name}", kw, repeat
            )
            stats["vs_today"] = b.compare(dref, st)
            res["denoise"][name] = stats
        results[title] = res
        (out / f"version_{label}.json").write_text(json.dumps(results, indent=1))
    b.log.info("done: %s", out / f"version_{label}.json")


if __name__ == "__main__":
    b.log.info("audio-separator %s from %s", VERSION, audio_separator.__file__)
    if sys.argv[1] == "prepare":
        prepare(Path(sys.argv[2]), sys.argv[3].split(","))
    else:
        bench(Path(sys.argv[2]))
