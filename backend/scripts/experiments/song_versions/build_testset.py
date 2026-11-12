"""
Freeze the song versions test set: real versions and controls from the dev library.

Real versions:
  - "pair": every song whose artist + title (brackets and " - ..." dropped)
    matches another song's, when their lengths differ by more than 20 s.
  - "untimed singing": songs with the most lead singing (singing map) more than
    2 s before the first or after the last timed word, at most two per artist.
  - "added": songs passed with --add.
Controls: songs from the lyrics benchmark's test set (LRC lines land on
singing), one per artist, with word timing and a singing map.

Synthetic versions are added later by synth.py.

Reads the database, writes only results/testset.json. Run from backend/:

    python scripts/experiments/song_versions/build_testset.py
    python scripts/experiments/song_versions/build_testset.py --add <song_id> --force

See docs/plans/2026-11-10-song-versions.md.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from common import (
    LIBRARY_DIR,
    TESTSET_PATH,
    Interval,
    TestSong,
    album_lines,
)
from sqlalchemy import text  # noqa: E402

from app.db.database import engine  # noqa: E402  (common.py puts backend/ on sys.path)

BENCHMARK_TESTSET = (
    Path(__file__).resolve().parents[1]
    / "lyrics_benchmark"
    / "results"
    / "testset.json"
)
PAIR_MIN_LENGTH_GAP = 20.0
# Singing this far from the first/last timed word doesn't count as untimed.
UNTIMED_MARGIN = 2.0
UNTIMED_MIN_SECONDS = 15.0
MAX_PER_ARTIST = 2
MAX_DURATION = 15 * 60


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _norm(value: Optional[str]) -> str:
    value = re.sub(r"\s*[\(\[].*?[\)\]]", "", value or "")
    value = re.sub(r"\s+-\s+.*$", "", value)
    return value.strip().lower()


def _rows() -> list[dict[str, Any]]:
    query = text("""
        SELECT id, title, artist, album, duration, language, synced_lyrics,
               word_synced_lyrics, singing_map
        FROM songs
        ORDER BY id
        """)
    with engine.connect() as conn:
        return [dict(row._mapping) for row in conn.execute(query)]


def _words(row: dict[str, Any]) -> list[dict[str, Any]]:
    alignment = _json(row["word_synced_lyrics"]) or {}
    return alignment.get("words") or []


def _intervals(row: dict[str, Any], key: str) -> Optional[list[Interval]]:
    singing_map = _json(row["singing_map"]) or {}
    value = singing_map.get(key)
    return None if value is None else [(float(a), float(b)) for a, b in value]


def _untimed(row: dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
    words = _words(row)
    lead = _intervals(row, "lead")
    if not words or lead is None:
        return None, None
    first = min(w["start"] for w in words) - UNTIMED_MARGIN
    last = max(w["end"] for w in words) + UNTIMED_MARGIN
    before = sum(max(0.0, min(b, first) - a) for a, b in lead)
    after = sum(max(0.0, b - max(a, last)) for a, b in lead)
    return round(before, 1), round(after, 1)


def _usable(row: dict[str, Any]) -> Optional[str]:
    """Why a song can't be in the set, or None."""
    if not (LIBRARY_DIR / row["id"] / "vocals.mp3").exists():
        return "no vocals.mp3"
    if row["duration"] and row["duration"] > MAX_DURATION:
        return "too long"
    return None


def _song(
    row: dict[str, Any],
    kind: str,
    picked_as: str,
    pairs: list[dict[str, Any]],
    overrides: dict[str, str],
) -> Optional[TestSong]:
    # Album lyrics: the song's own synced lyrics, else the shortest pair's.
    source = row
    if not (row["synced_lyrics"] or "").strip() or not album_lines(
        row["synced_lyrics"]
    ):
        with_lyrics = [p for p in pairs if album_lines(p["synced_lyrics"] or "")]
        if not with_lyrics:
            return None
        source = min(with_lyrics, key=lambda p: p["duration"] or 0)

    if row["id"] in overrides:
        language, language_source = overrides[row["id"]], "manual"
    else:
        # A detection on treated or live vocals can be wrong (Terrible Lie live:
        # "pt"), so the versions share one language: the one of the version
        # whose stored alignment scores best.
        group = [p for p in [row, *pairs] if p["language"]]
        best = max(
            group,
            key=lambda p: (_json(p["word_synced_lyrics"]) or {}).get("mean_score") or 0,
            default=None,
        )
        if best is None:
            language, language_source = "en", "default"
        elif best["id"] == row["id"]:
            language, language_source = row["language"], "song"
        else:
            language, language_source = best["language"], "pair"

    alignment = _json(row["word_synced_lyrics"]) or {}
    words = alignment.get("words") or []
    before, after = _untimed(row)
    return TestSong(
        song_id=row["id"],
        kind=kind,  # type: ignore[typeddict-item]
        picked_as=picked_as,
        title=row["title"],
        artist=row["artist"],
        duration=row["duration"],
        song_dir=str(LIBRARY_DIR / row["id"]),
        language=language,
        language_source=language_source,
        album_lrc=source["synced_lyrics"],
        album_from=source["id"],
        pair_ids=[p["id"] for p in pairs],
        today=(
            {
                "lrc": row["synced_lyrics"] or "",
                "words": words,
                "mean_score": alignment.get("mean_score"),
            }
            if words
            else None
        ),
        lead=_intervals(row, "lead"),
        backing=_intervals(row, "backing"),
        truth=None,
        untimed_before=before,
        untimed_after=after,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[1])
    parser.add_argument("--untimed", type=int, default=20, help="untimed-singing songs")
    parser.add_argument("--controls", type=int, default=15)
    parser.add_argument("--add", nargs="*", default=[], help="song ids to add as real")
    parser.add_argument(
        "--language",
        nargs="*",
        default=[],
        metavar="SONG_ID=CODE",
        help="language overrides, e.g. a741eb92-...=en",
    )
    parser.add_argument("--force", action="store_true", help="replace the test set")
    args = parser.parse_args()

    if TESTSET_PATH.exists() and not args.force:
        raise SystemExit(
            f"{TESTSET_PATH} exists. Results are only comparable on the same set; "
            "pass --force to replace it."
        )
    overrides = dict(item.split("=", 1) for item in args.language)

    rows = _rows()
    by_id = {row["id"]: row for row in rows}
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(_norm(row["artist"]), _norm(row["title"]))].append(row)
    pairs_of = {
        row["id"]: [p for p in group if p["id"] != row["id"]]
        for group in groups.values()
        for row in group
    }

    songs: list[TestSong] = []
    taken: set[str] = set()
    skipped: dict[str, int] = defaultdict(int)

    def take(row: dict[str, Any], kind: str, picked_as: str) -> bool:
        if row["id"] in taken:
            return False
        problem = _usable(row)
        song = (
            None
            if problem
            else _song(row, kind, picked_as, pairs_of[row["id"]], overrides)
        )
        if song is None:
            skipped[problem or "no album lyrics"] += 1
            return False
        songs.append(song)
        taken.add(row["id"])
        return True

    for song_id in args.add:
        if song_id not in by_id:
            raise SystemExit(f"No song {song_id}")
        take(by_id[song_id], "real", "added")

    for group in groups.values():
        lengths = [row["duration"] or 0 for row in group]
        if len(group) > 1 and max(lengths) - min(lengths) > PAIR_MIN_LENGTH_GAP:
            for row in group:
                take(row, "real", "pair")

    untimed = []
    for row in rows:
        before, after = _untimed(row)
        if before is not None and after is not None:
            if before + after >= UNTIMED_MIN_SECONDS:
                untimed.append((before + after, row))
    untimed.sort(key=lambda item: -item[0])
    per_artist: dict[str, int] = defaultdict(int)
    added = 0
    for _, row in untimed:
        if added >= args.untimed:
            break
        artist = _norm(row["artist"])
        if per_artist[artist] >= MAX_PER_ARTIST:
            continue
        if take(row, "real", "untimed singing"):
            per_artist[artist] += 1
            added += 1

    if BENCHMARK_TESTSET.exists():
        benchmark = json.loads(BENCHMARK_TESTSET.read_text())["songs"]
        control_artists: set[str] = set()
        added = 0
        for entry in benchmark:
            if added >= args.controls:
                break
            row = by_id.get(entry["song_id"])
            if row is None or not _words(row) or _intervals(row, "lead") is None:
                continue
            artist = _norm(row["artist"])
            if artist in control_artists:
                continue
            if take(row, "control", "control"):
                control_artists.add(artist)
                added += 1
    else:
        print(f"No lyrics benchmark test set at {BENCHMARK_TESTSET}: no controls")

    TESTSET_PATH.parent.mkdir(parents=True, exist_ok=True)
    TESTSET_PATH.write_text(
        json.dumps(
            {
                "built_at": datetime.now(timezone.utc).isoformat(),
                "songs": songs,
            },
            indent=1,
            ensure_ascii=False,
        )
    )
    counts: dict[str, int] = defaultdict(int)
    for song in songs:
        counts[f"{song['kind']}/{song['picked_as']}"] += 1
    print(f"Wrote {len(songs)} songs to {TESTSET_PATH}")
    for key, count in sorted(counts.items()):
        print(f"  {key}: {count}")
    for reason, count in sorted(skipped.items()):
        print(f"  skipped ({reason}): {count}")


if __name__ == "__main__":
    main()
