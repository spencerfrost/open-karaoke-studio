"""
Does aligning against lead + backing vocals beat aligning against the lead alone?

Alignment today hears only vocals.mp3, the lead stem, and two in three crammed
lines are sung by the backing stem alone. This re-aligns each test song's
stored LRC twice with the production aligner, once on the lead stem and once
on a mix of the lead and backing stems, and counts bad lines both ways with
crammed_lines.py's rules. Nothing is written to the database.

Test songs:
- worst: songs with the most crammed lines that are sung by the backing stem
  alone, the songs this should help;
- control: songs with no bad lines today and some backing singing, which
  must not get worse.

Export the songs first (read-only), then run from backend/ with the venv:

    psql "$DATABASE_URL" -c "copy (select id, title, artist, language,
        synced_lyrics, word_synced_lyrics, singing_map from songs
        where word_synced_lyrics is not null and singing_map is not null)
        to stdout with (format csv, header)" > songs.csv
    python scripts/experiments/align_on_mix.py songs.csv [--worst 40] [--control 40]

Results go to the word timing experiments folder (gitignored), one file per
song, so a rerun skips songs already done. The admin Compare word timing page
reads them to check the changed lines by ear. See
docs/plans/2026-10-28-lyrics-roadmap.md.
"""

import argparse
import csv
import itertools
import json
import logging
import os
import random
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import crammed_lines  # noqa: E402  (same folder)

from app.services.word_timing_experiments import EXPERIMENTS_DIR  # noqa: E402

csv.field_size_limit(10**9)

CONDITIONS = ("lead", "mix")
EXPERIMENT_ID = "align_on_mix"
META = {
    "name": "Lead + backing vocals",
    "description": (
        "Each song's lyrics aligned twice with the production aligner: against the lead "
        "vocals alone, as today, and against the lead and backing vocals mixed."
    ),
    "a": {"key": "lead", "label": "Lead only (today)"},
    "b": {"key": "mix", "label": "Lead + backing"},
    "groups": [
        {
            "key": "worst",
            "label": "Should help: crammed lines sung by the backing vocals",
        },
        {"key": "control", "label": "Controls: no bad lines today"},
    ],
}


def lines_of(words: Sequence[Mapping]) -> list[list]:
    lines = [
        list(g) for _, g in itertools.groupby(words, key=lambda w: w["line_index"])
    ]
    return [line for line in lines if len(line) >= 3]


def count_bad(words: Sequence[Mapping], singing_map: dict) -> dict:
    lines = lines_of(words)
    crammed = [crammed_lines.is_crammed(line) for line in lines]
    held = [crammed_lines.is_held(line, singing_map) for line in lines]
    backing_only = sum(
        c and crammed_lines.who_sings(line, singing_map) == "backing only"
        for line, c in zip(lines, crammed)
    )
    return {
        "lines": len(lines),
        "crammed": sum(crammed),
        "crammed_backing_only": backing_only,
        "held": sum(held),
        "bad": sum(c or h for c, h in zip(crammed, held)),
    }


def pick_songs(
    rows: list[dict], worst: int, control: int, seed: int
) -> list[tuple[str, dict]]:
    scored = []
    for row in rows:
        if not row["synced_lyrics"].strip():
            continue
        singing_map = json.loads(row["singing_map"])
        stored = count_bad(json.loads(row["word_synced_lyrics"])["words"], singing_map)
        backing_sung = sum(b - a for a, b in singing_map.get("backing") or [])
        scored.append((row, stored, backing_sung))

    by_backing_cram = sorted(scored, key=lambda s: -s[1]["crammed_backing_only"])
    worst_rows = [
        s[0] for s in by_backing_cram[:worst] if s[1]["crammed_backing_only"] > 0
    ]

    clean = [
        s[0] for s in scored if s[1]["bad"] == 0 and s[2] >= 20 and s[1]["lines"] >= 10
    ]
    random.Random(seed).shuffle(clean)
    return [("worst", r) for r in worst_rows] + [
        ("control", r) for r in clean[:control]
    ]


def write_mix(library: Path, song_id: str, out_dir: Path) -> Path:
    import librosa
    import numpy as np
    import soundfile as sf

    # Alignment reads the folder name as the song id.
    path = out_dir / "mix" / song_id / "vocals.wav"
    lead, sr = librosa.load(str(library / song_id / "vocals.mp3"), sr=None, mono=True)
    backing, _ = librosa.load(
        str(library / song_id / "backing_vocals.mp3"), sr=sr, mono=True
    )
    n = max(len(lead), len(backing))
    mix = np.pad(lead, (0, n - len(lead))) + np.pad(backing, (0, n - len(backing)))
    peak = float(np.max(np.abs(mix))) or 1.0
    if peak > 1.0:
        mix = mix / peak
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), mix, sr)
    return path


def run_song(group: str, row: dict, library: Path, out_dir: Path) -> dict:
    from app.services.lyrics_alignment import align_lyrics_to_vocals

    singing_map = json.loads(row["singing_map"])
    stored = json.loads(row["word_synced_lyrics"])
    language = row.get("language") or stored.get("language") or "en"
    mix_path = write_mix(library, row["id"], out_dir)
    audio = {"lead": library / row["id"] / "vocals.mp3", "mix": mix_path}
    result = {
        "id": row["id"],
        "artist": row["artist"],
        "title": row["title"],
        "group": group,
        "stored": count_bad(stored["words"], singing_map),
    }
    for condition in CONDITIONS:
        aligned = align_lyrics_to_vocals(
            row["synced_lyrics"],
            audio[condition],
            language=language,
            alignment_mode="synced",
        )
        if not aligned:
            result[condition] = None
            continue
        result[condition] = count_bad(aligned["words"], singing_map) | {
            "mean_score": aligned["mean_score"],
            "words": aligned["words"],
        }
    mix_path.unlink()  # about 20 MB a song
    mix_path.parent.rmdir()
    return result


def summarize(results: list[dict]) -> None:
    def pct(n: int, d: int) -> str:
        return f"{n / d:5.1%}" if d else "  -  "

    for group in ("worst", "control"):
        done = [r for r in results if r["group"] == group and r["lead"] and r["mix"]]
        if not done:
            continue
        print(f"\n{group}: {len(done)} songs")
        print(f"  {'':8} {'crammed':>8} {'held':>8} {'bad':>8} {'score':>6}")
        for condition in ("stored",) + CONDITIONS:
            lines = sum(r[condition]["lines"] for r in done)
            row = [
                pct(sum(r[condition][k] for r in done), lines)
                for k in ("crammed", "held", "bad")
            ]
            scores = [
                r[condition]["mean_score"] for r in done if "mean_score" in r[condition]
            ]
            score = f"{sum(scores) / len(scores):.3f}" if scores else ""
            print(f"  {condition:8} {row[0]:>8} {row[1]:>8} {row[2]:>8} {score:>6}")
        better = sum(r["mix"]["bad"] < r["lead"]["bad"] for r in done)
        worse = sum(r["mix"]["bad"] > r["lead"]["bad"] for r in done)
        print(
            f"  mix vs lead, songs: {better} better, {worse} worse, {len(done) - better - worse} same"
        )
        moved = sorted(
            done,
            key=lambda r: (r["mix"]["bad"] - r["lead"]["bad"]) / r["lead"]["lines"],
        )
        for r in moved[:5] + moved[max(5, len(moved) - 5) :]:
            print(
                f"    bad {r['lead']['bad']:>3} -> {r['mix']['bad']:<3} of {r['lead']['lines']:<3}"
                f" score {r['lead']['mean_score']:.2f} -> {r['mix']['mean_score']:.2f}"
                f"  {r['artist']} - {r['title']}"
            )
    failed = [r for r in results if not (r["lead"] and r["mix"])]
    if failed:
        print(f"\nalignment failed: {', '.join(r['title'] for r in failed)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--out-dir", type=Path, default=EXPERIMENTS_DIR / EXPERIMENT_ID)
    parser.add_argument("--worst", type=int, default=40)
    parser.add_argument("--control", type=int, default=40)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--library", type=Path, default=Path(os.environ.get("LIBRARY_DIR", ""))
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    rows = list(csv.DictReader(open(args.csv_path)))
    songs = pick_songs(rows, args.worst, args.control, args.seed)
    results_dir = args.out_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "meta.json").write_text(json.dumps(META, indent=1))

    results = []
    for i, (group, row) in enumerate(songs, 1):
        path = results_dir / f"{row['id']}.json"
        if path.exists():
            results.append(json.loads(path.read_text()))
            continue
        print(
            f"[{i}/{len(songs)}] {group} {row['artist']} - {row['title']}", flush=True
        )
        try:
            result = run_song(group, row, args.library, args.out_dir)
        except Exception as error:  # one bad song shouldn't stop the run
            print(f"  failed: {error}", flush=True)
            continue
        path.write_text(json.dumps(result))
        results.append(result)

    summarize(results)


if __name__ == "__main__":
    main()
