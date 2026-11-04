"""
Count word-timed lines where the aligner crammed words it couldn't hear.

A crammed line freezes on one word, then flashes through the rest packed one
frame apart with scores near zero. Same rule as the player's
isWordTimingCrammed (frontend activeLineTiming.ts); keep the two in step.
See docs/plans/2026-10-28-lyrics-roadmap.md.

Export the songs first (read-only), then run on the CSV:

    psql "$DATABASE_URL" -c "copy (select id, title, artist, word_synced_lyrics
        from songs where word_synced_lyrics is not null)
        to stdout with (format csv, header)" > words.csv
    python scripts/experiments/crammed_lines.py words.csv [per_song.json]
"""

import csv
import itertools
import json
import sys

csv.field_size_limit(10**9)

UNHEARD_SCORE = 0.1  # below this the aligner didn't really find the word
PACKED_STEP_SEC = 0.1  # start-to-start step that counts as packed


def is_crammed(words: list[dict]) -> bool:
    if len(words) < 3:
        return False

    packed_unheard = sum(
        1
        for prev, word in zip(words, words[1:])
        if word["score"] < UNHEARD_SCORE and word["start"] - prev["start"] < PACKED_STEP_SEC
    )
    if packed_unheard >= max(2, 0.4 * (len(words) - 1)):
        return True

    span = words[-1]["end"] - words[0]["start"]
    if span <= 1:
        return False
    for i, word in enumerate(words[:-1]):
        if (word["end"] - word["start"]) / span > 0.5:
            after = words[i + 1 :]
            unheard = sum(1 for w in after if w["score"] < UNHEARD_SCORE * 2)
            return unheard >= max(1, len(after) / 2)
    return False


def main(csv_path: str, out_path: str | None) -> None:
    songs = []
    for row in csv.DictReader(open(csv_path)):
        meta = json.loads(row["word_synced_lyrics"])
        lines = [
            list(group)
            for _, group in itertools.groupby(meta["words"], key=lambda w: w["line_index"])
        ]
        scored = [line for line in lines if len(line) >= 3]
        bad = sum(is_crammed(line) for line in scored)
        songs.append(
            {
                "id": row["id"],
                "artist": row["artist"],
                "title": row["title"],
                "lines": len(scored),
                "crammed": bad,
                "fraction": bad / len(scored) if scored else 0,
                "mean_score": meta.get("mean_score") or 0,
                "retimed_by": meta.get("retimed_by"),
            }
        )

    total_lines = sum(s["lines"] for s in songs)
    total_bad = sum(s["crammed"] for s in songs)
    print(f"{len(songs)} songs, {total_bad}/{total_lines} lines crammed ({total_bad / total_lines:.1%})")
    print(f"  songs with any: {sum(s['crammed'] > 0 for s in songs)}")
    print(f"  songs with >=15%: {sum(s['fraction'] >= 0.15 for s in songs)}")
    print("\nworst 20:")
    for s in sorted(songs, key=lambda s: -s["fraction"])[:20]:
        print(f"  {s['fraction']:.0%} ({s['crammed']}/{s['lines']}) {s['artist']} - {s['title']}")

    if out_path:
        json.dump(songs, open(out_path, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
