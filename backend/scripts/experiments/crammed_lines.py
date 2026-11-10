"""
Count word-timed lines whose word timing is wrong in a way singers see.

Two kinds of bad line:

- Crammed: the line freezes on one word, then flashes through the rest packed
  one frame apart with scores near zero. Same rule as the player's
  isWordTimingCrammed (frontend activeLineTiming.ts); keep the two in step.
- Held: the last word stays lit through silence ("mine" held 19 s in A Perfect
  Circle "The Package", score 0.97). A score marks a word's start, not its
  length, so this needs the singing map: songs without one can't be checked,
  and the player can't apply this rule.

See docs/plans/2026-10-28-lyrics-roadmap.md.

Export the songs first (read-only), then run on the CSV:

    psql "$DATABASE_URL" -c "copy (select id, title, artist, word_synced_lyrics,
        singing_map from songs where word_synced_lyrics is not null)
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
HELD_SILENCE_SEC = 2.0  # silence on both stems inside the last word that counts as held


def is_crammed(words: list[dict]) -> bool:
    if len(words) < 3:
        return False

    packed_unheard = sum(
        1
        for prev, word in zip(words, words[1:])
        if word["score"] < UNHEARD_SCORE
        and word["start"] - prev["start"] < PACKED_STEP_SEC
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


def longest_silence(intervals: list[list[float]], start: float, end: float) -> float:
    """Longest stretch of [start, end] that no interval covers."""
    longest = 0.0
    covered_to = start
    for a, b in sorted(intervals):
        if b <= start or a >= end:
            continue
        longest = max(longest, a - covered_to)
        covered_to = max(covered_to, min(b, end))
    return max(longest, end - covered_to)


def coverage(intervals: list[list[float]], start: float, end: float) -> float:
    """Share of [start, end] that the intervals cover."""
    if end <= start:
        return 0.0
    covered = 0.0
    covered_to = start
    for a, b in sorted(intervals):
        a, b = max(a, covered_to), min(b, end)
        if b > a:
            covered += b - a
            covered_to = b
    return covered / (end - start)


SINGING_SHARE = 0.5  # share of a line a stem must cover to count as singing during it


def who_sings(words: list[dict], singing_map: dict) -> str:
    """Which stems are singing during a line: "lead", "backing only" or "neither"."""
    start, end = words[0]["start"], words[-1]["end"]
    if coverage(singing_map.get("lead") or [], start, end) >= SINGING_SHARE:
        return "lead"
    if coverage(singing_map.get("backing") or [], start, end) >= SINGING_SHARE:
        return "backing only"
    return "neither"


def is_held(words: list[dict], singing_map: dict) -> bool:
    sound = (singing_map.get("lead") or []) + (singing_map.get("backing") or [])
    last = words[-1]
    return longest_silence(sound, last["start"], last["end"]) >= HELD_SILENCE_SEC


def main(csv_path: str, out_path: str | None) -> None:
    songs = []
    for row in csv.DictReader(open(csv_path)):
        meta = json.loads(row["word_synced_lyrics"])
        lines = [
            list(group)
            for _, group in itertools.groupby(
                meta["words"], key=lambda w: w["line_index"]
            )
        ]
        scored = [line for line in lines if len(line) >= 3]
        singing_map = json.loads(row["singing_map"]) if row.get("singing_map") else None
        crammed = [is_crammed(line) for line in scored]
        held = [bool(singing_map) and is_held(line, singing_map) for line in scored]
        bad = sum(c or h for c, h in zip(crammed, held))
        during = {"lead": 0, "backing only": 0, "neither": 0}
        if singing_map:
            for line, c in zip(scored, crammed):
                if c:
                    during[who_sings(line, singing_map)] += 1
        songs.append(
            {
                "id": row["id"],
                "artist": row["artist"],
                "title": row["title"],
                "lines": len(scored),
                "has_map": singing_map is not None,
                "crammed": sum(crammed),
                "held": sum(held),
                "bad": bad,
                "crammed_during": during,
                "fraction": bad / len(scored) if scored else 0,
                "mean_score": meta.get("mean_score") or 0,
                "retimed_by": meta.get("retimed_by"),
            }
        )

    def rate(n: int, d: int) -> str:
        return f"{n}/{d} ({n / d:.1%})" if d else "0/0"

    total_lines = sum(s["lines"] for s in songs)
    mapped = [s for s in songs if s["has_map"]]
    mapped_lines = sum(s["lines"] for s in mapped)
    print(f"{len(songs)} songs, {total_lines} lines")
    print(f"  crammed: {rate(sum(s['crammed'] for s in songs), total_lines)}")
    if mapped:
        print(f"  songs with a singing map: {len(mapped)}, {mapped_lines} lines")
        print(
            f"    held last word: {rate(sum(s['held'] for s in mapped), mapped_lines)}"
        )
        print(
            f"    bad (crammed or held): {rate(sum(s['bad'] for s in mapped), mapped_lines)}"
        )
        mapped_crammed = sum(s["crammed"] for s in mapped)
        print("    crammed lines, by who is singing during them:")
        for who in ("lead", "backing only", "neither"):
            n = sum(s["crammed_during"][who] for s in mapped)
            print(f"      {who}: {rate(n, mapped_crammed)}")
    else:
        print("  no singing maps: held last words not checked")
    print(f"  songs with any bad line: {sum(s['bad'] > 0 for s in songs)}")
    print(f"  songs with >=15%: {sum(s['fraction'] >= 0.15 for s in songs)}")
    print("\nworst 20:")
    for s in sorted(songs, key=lambda s: -s["fraction"])[:20]:
        print(
            f"  {s['fraction']:.0%} ({s['crammed']} crammed, {s['held']} held /{s['lines']})"
            f" {s['artist']} - {s['title']}"
        )

    if out_path:
        json.dump(songs, open(out_path, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
