#!/usr/bin/env python3
"""The engine's step 4: three WAV -> MP3 exports, sequential vs parallel.

Inputs are three 16-bit stereo WAVs the length of the song (Demucs vocals,
instrumental and a second-seed vocals standing in for the backing), written
from original.mp3 the way the engine writes its intermediates. Methods:

  pydub         today: AudioSegment.from_wav + export, one stem after another
  pydub_par     the same three exports in threads
  ffmpeg        ffmpeg run directly on the WAV with pydub's arguments
  ffmpeg_par    the same three in parallel

Each at the bitrate string the engine passes ("320", which ffmpeg reads as
bits/s and replaces with its 128 kb/s default) and at "320k". Reports best of
--repeats wall time and whether each output's audio matches today's bytes.

    mp3_export_bench.py <out_dir> <song_id>,<song_id> [--repeats N]
"""

import hashlib
import json
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import soundfile as sf
import torch
from pydub import AudioSegment

sys.path.insert(0, str(Path(__file__).parent))
import demucs_variants_bench as dv  # noqa: E402
import vram_quality_bench as b  # noqa: E402

STEMS = ("vocals", "backing_vocals", "instrumental")


def write_inputs(sd: Path, song_id: str) -> dict[str, Path]:
    paths = {s: sd / f"{s}.wav" for s in STEMS}
    if all(p.exists() for p in paths.values()):
        return paths
    sep = dv.make_separator()
    wav = sep._load_audio(b.LIB / song_id / "original.mp3")
    for seed, names in ((0, ("vocals", "instrumental")), (1, ("backing_vocals",))):
        random.seed(seed)
        torch.manual_seed(seed)
        mix, stems = sep.separate_tensor(wav)
        v = stems["vocals"].cpu()
        audio = {"vocals": v, "backing_vocals": v, "instrumental": mix.cpu() - v}
        for n in names:
            sf.write(str(paths[n]), audio[n].numpy().T, sep.samplerate, "PCM_16")
    del sep
    b.free_gpu()
    return paths


def pydub_export(src: Path, dst: Path, bitrate: str):
    AudioSegment.from_wav(str(src)).export(str(dst), format="mp3", bitrate=bitrate)


def ffmpeg_export(src: Path, dst: Path, bitrate: str):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "wav", "-i", str(src)]
    cmd += ["-acodec", "libmp3lame", "-b:a", bitrate, "-f", "mp3", str(dst)]
    subprocess.run(cmd, check=True)


def audio_md5(path: Path) -> str:
    """MD5 of the MP3 frames, ignoring the ID3 tag (it holds the encoder name)."""
    data = path.read_bytes()
    if data[:3] == b"ID3":
        size = 0
        for byte in data[6:10]:
            size = (size << 7) | byte
        data = data[10 + size :]
    return hashlib.md5(data).hexdigest()


def run(method: str, inputs: dict[str, Path], od: Path, bitrate: str):
    od.mkdir(parents=True, exist_ok=True)
    fn = pydub_export if method.startswith("pydub") else ffmpeg_export
    jobs = [(inputs[s], od / f"{s}.mp3", bitrate) for s in STEMS]
    t0 = time.perf_counter()
    if method.endswith("_par"):
        with ThreadPoolExecutor(len(jobs)) as pool:
            list(pool.map(lambda j: fn(*j), jobs))
    else:
        per = {}
        for s, j in zip(STEMS, jobs):
            t = time.perf_counter()
            fn(*j)
            per[s] = round(time.perf_counter() - t, 2)
    total = time.perf_counter() - t0
    return total, (per if not method.endswith("_par") else None)


def bench_song(out: Path, song_id: str, repeats: int):
    title = json.load(open(b.LIB / song_id / "original.info.json")).get("title")
    sd = out / song_id
    sd.mkdir(parents=True, exist_ok=True)
    b.log.info("=== %s", title)
    inputs = write_inputs(sd, song_id)
    res: dict = {"title": title}
    for bitrate in ("320", "320k"):
        ref = None
        for method in ("pydub", "pydub_par", "ffmpeg", "ffmpeg_par"):
            od = sd / f"{method}_{bitrate}"
            best, per = None, None
            for _ in range(repeats):
                total, p = run(method, inputs, od, bitrate)
                if best is None or total < best:
                    best, per = total, p
            md5 = {s: audio_md5(od / f"{s}.mp3") for s in STEMS}
            ref = ref or md5
            kbps = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "stream=bit_rate",
                    "-of",
                    "csv=p=0",
                    str(od / "vocals.mp3"),
                ],
                capture_output=True,
                text=True,
            ).stdout.strip()
            row = {
                "seconds": round(best, 2),
                "per_stem_s": per,
                "kbps": int(kbps) // 1000,
                "same_audio_as_pydub": md5 == ref,
            }
            res[f"{method}@{bitrate}"] = row
            b.log.info("%s@%s: %s", method, bitrate, row)
    return res


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    repeats = 3
    if "--repeats" in sys.argv:
        repeats = int(sys.argv[sys.argv.index("--repeats") + 1])
        args.remove(str(repeats))
    out = Path(args[0])
    out.mkdir(parents=True, exist_ok=True)
    allres = [bench_song(out, s, repeats) for s in args[1].split(",")]
    (out / "mp3_export.json").write_text(json.dumps(allres, indent=1))
    print(json.dumps(allres, indent=1))
