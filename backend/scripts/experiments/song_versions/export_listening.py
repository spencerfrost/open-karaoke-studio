"""
Put today against a method on the admin Compare word timing page, for the
real versions the detection rule flags.

Only methods that keep today's lines (album lines in album order, no
transcript text) can go there: the page pairs lines by number. A flagged song
goes on the page when the method changes how much lead singing has an album
line on screen by more than --min-change, grouped by which way.

    python scripts/experiments/song_versions/export_listening.py
    python scripts/experiments/song_versions/export_listening.py \\
        --method retime-inorder-anchors@whisper-small --id song_versions_retime

Run score.py first. Writes the experiment folder under the word timing
experiments directory (gitignored); nothing reaches the database.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from common import RESULTS_DIR, RUNS_DIR, load_testset

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import crammed_lines  # noqa: E402  (experiments/)

from app.services.word_timing_experiments import EXPERIMENTS_DIR  # noqa: E402

UNTIMED_FLAG_SECONDS = 15.0
ALWAYS = {"a741eb92-1958-453c-8d28-c917e3e7b55d"}  # Terrible Lie (live)


def count_bad(words: list[dict[str, Any]], singing_map: dict[str, Any]) -> dict:
    lines = [
        list(g)
        for _, g in itertools.groupby(
            sorted(words, key=lambda w: (w["line_index"], w["start"])),
            key=lambda w: w["line_index"],
        )
    ]
    lines = [line for line in lines if len(line) >= 3]
    crammed = [crammed_lines.is_crammed(line) for line in lines]
    held = [crammed_lines.is_held(line, singing_map) for line in lines]
    return {
        "lines": len(lines),
        "crammed": sum(crammed),
        "held": sum(held),
        "bad": sum(c or h for c, h in zip(crammed, held)),
    }


def by_album_line(result: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Words renumbered by album line; None if the run shows anything else."""
    lines = result["lines"]
    if any(line["source"] != "album" for line in lines):
        return None
    indices = [line["album_index"] for line in lines]
    if indices != sorted(set(indices)):
        return None  # repeats or reordering: lines wouldn't pair up
    return [
        {**w, "line_index": lines[w["line_index"]]["album_index"]}
        for w in result["words"]
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[1])
    parser.add_argument("--method", default="retime-inorder-anchors@whisper-small")
    parser.add_argument("--id", default="song_versions_retime")
    parser.add_argument("--name", default="Other versions: re-timed")
    parser.add_argument("--min-change", type=float, default=0.05)
    args = parser.parse_args()

    songs = {s["song_id"]: s for s in load_testset()}
    rows = {
        (r["run"], r["song_id"]): r
        for r in csv.DictReader(open(RESULTS_DIR / "per_song.csv"))
    }
    out = EXPERIMENTS_DIR / args.id
    if out.exists():
        shutil.rmtree(out / "results", ignore_errors=True)
    (out / "results").mkdir(parents=True, exist_ok=True)
    (out / "meta.json").write_text(
        json.dumps(
            {
                "name": args.name,
                "description": (
                    "Other versions of a song (live, remix, edit) flagged by ≥ 15 s of "
                    f"singing outside today's timed words: today's timing against "
                    f"{args.method}. Same lyrics, new timing."
                ),
                "a": {"key": "today", "label": "Today"},
                "b": {"key": "method", "label": args.method},
                "groups": [
                    {"key": "more", "label": "More singing under lyrics"},
                    {"key": "less", "label": "Less singing under lyrics"},
                ],
            },
            indent=1,
        )
    )

    written = 0
    for song_id, song in songs.items():
        if song["kind"] != "real":
            continue
        untimed = (song["untimed_before"] or 0) + (song["untimed_after"] or 0)
        if untimed < UNTIMED_FLAG_SECONDS and song_id not in ALWAYS:
            continue
        today_row = rows.get(("today", song_id))
        method_row = rows.get((args.method, song_id))
        if not today_row or not method_row or method_row.get("error"):
            continue
        change = float(method_row["covered_album"]) - float(today_row["covered_album"])
        if abs(change) <= args.min_change and song_id not in ALWAYS:
            continue
        today = json.loads((RUNS_DIR / "today" / f"{song_id}.json").read_text())
        method = json.loads((RUNS_DIR / args.method / f"{song_id}.json").read_text())
        a_words, b_words = by_album_line(today), by_album_line(method)
        if a_words is None or b_words is None:
            print(f"skip {song['title']}: lines don't pair up")
            continue
        singing_map = {"lead": song["lead"] or [], "backing": song["backing"]}
        (out / "results" / f"{song_id}.json").write_text(
            json.dumps(
                {
                    "id": song_id,
                    "title": song["title"],
                    "artist": song["artist"],
                    "group": "more" if change >= 0 else "less",
                    "today": {
                        **count_bad(a_words, singing_map),
                        "mean_score": today.get("mean_score"),
                        "words": a_words,
                    },
                    "method": {
                        **count_bad(b_words, singing_map),
                        "mean_score": method.get("mean_score"),
                        "words": b_words,
                    },
                }
            )
        )
        written += 1
        print(
            f"{'more' if change >= 0 else 'less'} {change:+.2f}  {song['artist']} - {song['title']}"
        )
    print(f"Wrote {written} songs to {out}")


if __name__ == "__main__":
    main()
