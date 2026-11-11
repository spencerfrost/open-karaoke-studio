"""
Does repairing word timing against the singing map follow the singer better?

The aligner holds words through silence and places some inside breaks
(app/services/word_timing_repair.py). This applies the repair to each song's
stored word timing and writes both versions for the admin Compare word timing
page, which lists every line the repair changed. Nothing is written to the
database and nothing is re-aligned, so it runs in seconds.

Groups, in the order to check them:
- cut: songs with a held word cut where the singing stops;
- moved: songs where a word only moved to where the singing starts again.

Export the songs first (read-only), then run from backend/ with the venv:

    psql "$DATABASE_URL" -c "copy (select id, title, artist, word_synced_lyrics,
        singing_map from songs where word_synced_lyrics is not null
        and singing_map is not null) to stdout with (format csv, header)" > songs.csv
    python scripts/experiments/repair_held_words.py songs.csv

Answers on the page are kept by line, so after the stored word timing changes
(a re-time), write a fresh experiment with --out-dir instead of over the old
one: the script refuses to overwrite an experiment that has answers.
See docs/plans/2026-10-28-lyrics-roadmap.md.
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from align_on_mix import count_bad  # noqa: E402  (same folder)

from app.services.word_timing_experiments import EXPERIMENTS_DIR  # noqa: E402
from app.services.word_timing_repair import repair_words  # noqa: E402

csv.field_size_limit(10**9)

EXPERIMENT_ID = "repair_held_words"
META = {
    "name": "Held words repaired",
    "description": (
        "Each song's stored word timing as the aligner left it, and repaired against "
        "the singing map: a word held into silence on both vocal tracks ends where "
        "the singing stops, and a word placed in a break moves to where the singing "
        "starts again. Watch when each word stops being lit, not only when it starts."
    ),
    "a": {"key": "aligner", "label": "Aligner (today)"},
    "b": {"key": "repaired", "label": "Repaired"},
    "groups": [
        {"key": "cut", "label": "Held words cut where the singing stops"},
        {"key": "moved", "label": "Words moved to where the singing starts"},
    ],
    "compareEnds": True,
}


def side(words: list[dict], singing_map: dict, mean_score: float | None) -> dict:
    return count_bad(words, singing_map) | {"words": words, "mean_score": mean_score}


def run_song(row: dict) -> tuple[dict, Counter] | None:
    stored = json.loads(row["word_synced_lyrics"])
    words = stored.get("words") or []
    if not words:
        return None
    singing_map = json.loads(row["singing_map"])
    repaired, changes = repair_words(words, singing_map)
    if not changes:
        return None
    kinds = Counter(change.kind for change in changes)
    mean_score = stored.get("mean_score")
    result = {
        "id": row["id"],
        "title": row["title"],
        "artist": row["artist"],
        "group": "cut" if kinds["cut"] else "moved",
        "changes": dict(kinds),
        "aligner": side(words, singing_map, mean_score),
        "repaired": side(repaired, singing_map, mean_score),
    }
    return result, kinds


def summarize(results: list[dict], kinds: Counter, songs_read: int) -> None:
    print(f"songs read: {songs_read}, changed: {len(results)}")
    for kind in ("cut", "start_moved", "moved"):
        print(f"  {kind:12} {kinds[kind]} words")
    for key in ("held", "crammed", "bad"):
        before = sum(r["aligner"][key] for r in results)
        after = sum(r["repaired"][key] for r in results)
        print(f"  {key:8} lines {before} -> {after}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--out-dir", type=Path, default=EXPERIMENTS_DIR / EXPERIMENT_ID)
    args = parser.parse_args()

    if (args.out_dir / "answers.json").exists():
        sys.exit(
            f"{args.out_dir} has answers from the page; "
            "write a new experiment with --out-dir instead"
        )

    rows = list(csv.DictReader(open(args.csv_path)))
    results_dir = args.out_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    for old in results_dir.glob("*.json"):
        old.unlink()  # a rerun reflects the current export only
    (args.out_dir / "meta.json").write_text(json.dumps(META, indent=1))

    results = []
    kinds: Counter = Counter()
    for row in rows:
        done = run_song(row)
        if done is None:
            continue
        result, song_kinds = done
        kinds.update(song_kinds)
        (results_dir / f"{row['id']}.json").write_text(json.dumps(result))
        results.append(result)

    summarize(results, kinds, len(rows))


if __name__ == "__main__":
    main()
