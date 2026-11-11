"""
Which songs got worse when the library was re-timed?

Takes two exports of the library's word timings, from before and after a
re-time, counts each song's bad lines (crammed or held, crammed_lines.py's
rules) both times, and puts the songs with more bad lines after on the admin
Compare word timing page, to hear whether they really got worse. Both sides
are counted against today's singing map, so only the word timing differs.

Songs whose words changed between the two exports (new lyrics, not a re-time)
are left out: their lines don't match up. Lines renumbered by added break
lines are matched up again.

Export the songs after the re-time (read-only), the same columns as before:

    psql "$DATABASE_URL" -c "copy (select id, title, artist, word_synced_lyrics,
        singing_map from songs where word_synced_lyrics is not null)
        to stdout with (format csv, header)" > after.csv
    python scripts/experiments/compare_retime.py before.csv after.csv \\
        --id retime_on_mix --name "Re-timed on lead + backing"

See docs/plans/2026-10-28-lyrics-roadmap.md.
"""

import argparse
import csv
import itertools
import json
import shutil
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import crammed_lines  # noqa: E402  (same folder)

from app.services.word_timing_experiments import EXPERIMENTS_DIR  # noqa: E402

csv.field_size_limit(10**9)


def load(path: str) -> dict[str, dict]:
    return {row["id"]: row for row in csv.DictReader(open(path))}


def count_bad(words: list[dict], singing_map: dict | None) -> dict:
    lines = [
        list(g) for _, g in itertools.groupby(words, key=lambda w: w["line_index"])
    ]
    lines = [line for line in lines if len(line) >= 3]
    crammed = [crammed_lines.is_crammed(line) for line in lines]
    held = [
        bool(singing_map) and crammed_lines.is_held(line, singing_map) for line in lines
    ]
    return {
        "lines": len(lines),
        "crammed": sum(crammed),
        "held": sum(held),
        "bad": sum(c or h for c, h in zip(crammed, held)),
    }


def renumbered(old: list[dict], new: list[dict]) -> list[dict] | None:
    """`old` with `new`'s line numbers, when both are the same words in order.

    A re-time can store its lyrics with blank break lines added, which
    renumbers every line after them. None when the words themselves differ.
    """

    def text(words: list[dict]) -> list[str]:
        return [w["word"].strip().lower() for w in words]

    if text(old) != text(new):
        return None
    lines = [[o["line_index"], n["line_index"]] for o, n in zip(old, new)]
    # The words of one old line must stay together on one new line.
    pairs = {(o, n) for o, n in lines}
    if len({o for o, _ in pairs}) != len(pairs):
        return None
    return [o | {"line_index": n["line_index"]} for o, n in zip(old, new)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("before_csv")
    parser.add_argument("after_csv")
    parser.add_argument("--id", default="retime")
    parser.add_argument("--name", default="Re-time")
    parser.add_argument("--before-label", default="Before the re-time")
    parser.add_argument("--after-label", default="After the re-time")
    args = parser.parse_args()

    before, after = load(args.before_csv), load(args.after_csv)
    songs, changed_words = [], 0
    for song_id, row in after.items():
        if song_id not in before:
            continue
        old_payload = json.loads(before[song_id]["word_synced_lyrics"])
        new_payload = json.loads(row["word_synced_lyrics"])
        old, new = old_payload["words"], new_payload["words"]
        old = renumbered(old, new)
        if old is None:
            changed_words += 1
            continue
        singing_map = json.loads(row["singing_map"]) if row.get("singing_map") else None
        songs.append(
            {
                "row": row,
                "old_words": old,
                "new_words": new,
                "before": count_bad(old, singing_map)
                | {"mean_score": old_payload.get("mean_score")},
                "after": count_bad(new, singing_map)
                | {"mean_score": new_payload.get("mean_score")},
            }
        )

    def total(side: str, key: str) -> int:
        return sum(s[side][key] for s in songs)

    lines = total("before", "lines")
    print(
        f"{len(songs)} songs in both exports with the same words"
        f" ({changed_words} left out: their words changed), {lines} lines"
    )
    for key in ("crammed", "held", "bad"):
        b, a = total("before", key), total("after", key)
        print(f"  {key:8} {b:>6} ({b / lines:.1%}) -> {a:>6} ({a / lines:.1%})")
    worse = [s for s in songs if s["after"]["bad"] > s["before"]["bad"]]
    better = [s for s in songs if s["after"]["bad"] < s["before"]["bad"]]
    print(
        f"  songs: {len(better)} better, {len(worse)} worse,"
        f" {len(songs) - len(better) - len(worse)} same"
    )
    worse.sort(key=lambda s: -(s["after"]["bad"] - s["before"]["bad"]))
    print("\nworse by the most lines:")
    for s in worse[:20]:
        print(
            f"  bad {s['before']['bad']:>3} -> {s['after']['bad']:<3} of {s['before']['lines']:<3}"
            f" {s['row']['artist']} - {s['row']['title']}"
        )

    out_dir = EXPERIMENTS_DIR / args.id
    if (out_dir / "results").exists():
        shutil.rmtree(out_dir / "results")  # answers.json is kept
    (out_dir / "results").mkdir(parents=True)
    meta = {
        "name": args.name,
        "description": (
            "Songs with more bad lines (crammed or held) after the re-time than before,"
            " the stored word timing before and after it."
        ),
        "a": {"key": "before", "label": args.before_label},
        "b": {"key": "after", "label": args.after_label},
        "groups": [{"key": "worse", "label": "More bad lines after the re-time"}],
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    for s in worse:
        row = s["row"]
        result = {
            "id": row["id"],
            "artist": row["artist"],
            "title": row["title"],
            "group": "worse",
            "before": s["before"] | {"words": s["old_words"]},
            "after": s["after"] | {"words": s["new_words"]},
        }
        (out_dir / "results" / f"{row['id']}.json").write_text(json.dumps(result))
    print(f"\n{len(worse)} songs written to {out_dir}")


if __name__ == "__main__":
    main()
