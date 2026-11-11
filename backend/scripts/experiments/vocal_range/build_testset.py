"""Freeze the vocal range test set: the plan's named songs plus a spread of others.

The extra songs are drawn evenly from four buckets of the range the app stores
today (narrow, typical, wide, not measured), at most one per artist, so the set
holds the suspicious tails as well as ordinary songs. Then the library's widest
stored ranges not already in the set ("widest", artists may repeat): the
failures most worth an ear check. Every song needs a
vocals.mp3. The set is frozen: results are only comparable on the same songs,
so --force is needed to rebuild it.

Usage (from backend/, venv active):
    python scripts/experiments/vocal_range/build_testset.py [--per-bucket 12]
"""

from __future__ import annotations

import argparse
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path

from common import TESTSET_PATH, Interval, TestSong, note_to_midi

from app.config import get_config  # noqa: E402  (common.py puts backend/ on sys.path)
from app.db.database import get_db_session  # noqa: E402
from app.db.models.song import DbSong  # noqa: E402
from app.services.lyrics_analysis import parse_lrc_lines  # noqa: E402

# The plan's test songs (docs/plans/2026-11-09-vocal-range.md), by id prefix.
NAMED = [
    "test-thumbnail-auto",  # Rick Astley, Never Gonna Give You Up
    "0fe64307",  # Kendrick Lamar, A.D.H.D
    "8f122f1d",  # OutKast, Ms. Jackson
    "5eb1a67a",  # Nine Inch Nails, Zero Sum
    "1e8e8a75",  # *NSYNC, Tearin' Up My Heart
    "59eb76d6",  # A Perfect Circle, Crimes
    "1a43ea4a",  # Pink Floyd, Bike
    "75b51054",  # Johnny Cash, One Piece at a Time
    "279df80f",  # Under the Influence of Giants, Heaven Is Full
]

# Stored width in semitones -> bucket. The dev library's quartiles were 11 and 20.
BUCKETS = ("narrow", "typical", "wide", "unmeasured")
# A lyric line lasts until the next one starts, but no longer than this.
MAX_LINE_SECONDS = 10.0


def width_bucket(low: str | None, high: str | None) -> str:
    if not low or not high:
        return "unmeasured"
    width = note_to_midi(high) - note_to_midi(low)
    if width <= 10:
        return "narrow"
    if width >= 24:
        return "wide"
    return "typical"


def artist_key(song: DbSong) -> str:
    if song.artist_id is not None:
        return f"id:{song.artist_id}"
    primary = re.split(
        r"\s+(?:feat\.?|ft\.?|featuring|&|x|and)\s+|,", song.artist.lower()
    )[0]
    return "name:" + " ".join(primary.split())


def lyric_lines(synced: str | None, duration: float | None) -> list[Interval] | None:
    if not synced:
        return None
    starts = [
        line["timestamp"] for line in parse_lrc_lines(synced) if line["text"].strip()
    ]
    if not starts:
        return None
    ends = starts[1:] + [starts[-1] + MAX_LINE_SECONDS]
    out = []
    for start, end in zip(starts, ends):
        end = min(end, start + MAX_LINE_SECONDS)
        if duration:
            end = min(end, duration)
        if end > start:
            out.append((round(start, 2), round(end, 2)))
    return out


def lead_intervals(singing_map: str | None) -> list[Interval] | None:
    if not singing_map:
        return None
    return [tuple(i) for i in json.loads(singing_map).get("lead", [])]


def to_test_song(song: DbSong, vocals: Path, picked_as: str) -> TestSong:
    return TestSong(
        song_id=song.id,
        title=song.title,
        artist=song.artist,
        duration=song.duration,
        vocals_path=str(vocals),
        stored_low=song.vocal_range_low,
        stored_high=song.vocal_range_high,
        picked_as=picked_as,
        lead_intervals=lead_intervals(song.singing_map),
        lyric_lines=lyric_lines(song.synced_lyrics, song.duration),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--per-bucket", type=int, default=12)
    parser.add_argument("--widest", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20261110)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if TESTSET_PATH.exists() and not args.force:
        raise SystemExit(f"{TESTSET_PATH} exists; --force rebuilds it")

    library = Path(get_config().BASE_LIBRARY_DIR)
    songs: list[TestSong] = []
    used_artists: set[str] = set()

    with get_db_session() as session:
        for prefix in NAMED:
            song = session.query(DbSong).filter(DbSong.id.like(prefix + "%")).one()
            vocals = library / song.id / "vocals.mp3"
            if not vocals.exists():
                print(f"skip named {prefix}: no vocals.mp3")
                continue
            songs.append(to_test_song(song, vocals, "named"))
            used_artists.add(artist_key(song))

        candidates: dict[str, list[DbSong]] = {b: [] for b in BUCKETS}
        for song in (
            session.query(DbSong)
            .filter(DbSong.status == "processed")
            .order_by(DbSong.id)
            .all()
        ):
            if not (library / song.id / "vocals.mp3").exists():
                continue
            candidates[
                width_bucket(song.vocal_range_low, song.vocal_range_high)
            ].append(song)

        rng = random.Random(args.seed)
        for bucket in BUCKETS:
            pool = candidates[bucket][:]
            rng.shuffle(pool)
            taken = 0
            for song in pool:
                if taken == args.per_bucket:
                    break
                key = artist_key(song)
                if key in used_artists:
                    continue
                used_artists.add(key)
                songs.append(
                    to_test_song(song, library / song.id / "vocals.mp3", bucket)
                )
                taken += 1
            print(f"{bucket}: {taken} of {len(candidates[bucket])} candidates")

        # Drawn last, so the buckets above pick the same songs with or without it.
        chosen = {s["song_id"] for s in songs}
        measured = [
            song
            for bucket in ("narrow", "typical", "wide")
            for song in candidates[bucket]
            if song.id not in chosen
        ]
        measured.sort(
            key=lambda song: (
                note_to_midi(song.vocal_range_low)
                - note_to_midi(song.vocal_range_high),
                song.id,
            )
        )
        for song in measured[: args.widest]:
            songs.append(to_test_song(song, library / song.id / "vocals.mp3", "widest"))
        print(f"widest: {min(args.widest, len(measured))}")

    TESTSET_PATH.parent.mkdir(parents=True, exist_ok=True)
    TESTSET_PATH.write_text(
        json.dumps(
            {
                "built_at": datetime.now(timezone.utc).isoformat(),
                "seed": args.seed,
                "songs": songs,
            },
            indent=1,
            ensure_ascii=False,
        )
    )
    print(f"{len(songs)} songs -> {TESTSET_PATH}")


if __name__ == "__main__":
    main()
