#!/usr/bin/env python3
"""Pick the benchmark songs from the library and freeze them into results/testset.json.

Read-only against the database. A song qualifies when:
- it has synced lyrics and a vocals.mp3 on disk,
- nobody has reported its lyrics,
- its LRC parses cleanly (times increase, all inside the song, enough lines and words),
- its line starts land on singing: checked against the vocals stem's loudness,
  not against any model, so the set doesn't favour the aligner we use today.

At most one song per artist, so the same artists can be held out of any
fine-tuning data later. The lyrics are copied into the file so the set
doesn't drift when lyrics are edited or re-fetched.

Run from backend/ with the venv active:
    python scripts/experiments/lyrics_benchmark/build_testset.py --size 80
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path

from common import (
    RESULTS_DIR,
    TESTSET_PATH,
    TestSong,
    load_vocals_16k,
    reference_lines,
    vocal_activity,
)
from sqlalchemy import text  # noqa: E402

from app.db.database import engine  # noqa: E402  (common.py puts backend/ on sys.path)

logger = logging.getLogger("build_testset")

MIN_LINES = 12
MIN_WORDS = 60
MAX_DURATION_SECONDS = 8 * 60
MIN_ONSET_ACTIVITY = 0.9


def artist_key(artist: str, artist_id: int | None) -> str:
    if artist_id is not None:
        return f"id:{artist_id}"
    primary = re.split(r"\s+(?:feat\.?|ft\.?|featuring|&|x|and)\s+|,", artist.lower())[
        0
    ]
    return "name:" + " ".join(primary.split())


def onset_activity(vocals_path: Path, line_starts: list[float]) -> tuple[float, float]:
    """Share of line starts with singing within [-0.5s, +1.5s], and the stem's length."""
    activity = vocal_activity(load_vocals_16k(str(vocals_path)))
    hits = 0
    for start in line_starts:
        lo = max(0, int((start - 0.5) * activity.frames_per_second))
        hi = min(
            len(activity.loud), int((start + 1.5) * activity.frames_per_second) + 1
        )
        hits += bool(activity.loud[lo:hi].any())
    return hits / len(line_starts), activity.duration


def candidate_rows() -> list[dict]:
    query = text("""
        SELECT s.id, s.title, s.artist, s.artist_id, s.language, s.duration,
               s.synced_lyrics
        FROM songs s
        WHERE s.synced_lyrics IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM lyrics_reports r WHERE r.song_id = s.id)
        ORDER BY s.id
        """)
    with engine.connect() as conn:
        return [dict(row._mapping) for row in conn.execute(query)]


def lrc_problem(lines, duration: float | None) -> str | None:
    if len(lines) < MIN_LINES:
        return "too few lines"
    if sum(len(line["text"].split()) for line in lines) < MIN_WORDS:
        return "too few words"
    starts = [line["start"] for line in lines]
    if any(b < a for a, b in zip(starts, starts[1:])):
        return "times go backwards"
    if duration and starts[-1] >= duration:
        return "lines past the end of the song"
    if duration and duration > MAX_DURATION_SECONDS:
        return "too long"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--size", type=int, default=80)
    parser.add_argument("--seed", type=int, default=20261010)
    parser.add_argument(
        "--library-dir",
        default=os.getenv(
            "LIBRARY_DIR", str(Path(__file__).resolve().parents[4] / "karaoke_library")
        ),
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite an existing test set"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if TESTSET_PATH.exists() and not args.force:
        raise SystemExit(
            f"{TESTSET_PATH} exists. Results are only comparable on the same set; "
            "pass --force to replace it."
        )

    from app.services.lyrics_language import detect_vocals_language, normalize_language

    rows = candidate_rows()
    random.Random(args.seed).shuffle(rows)
    library = Path(args.library_dir)

    songs: list[TestSong] = []
    seen_artists: set[str] = set()
    rejected: dict[str, int] = {}

    def reject(reason: str) -> None:
        rejected[reason] = rejected.get(reason, 0) + 1

    for row in rows:
        if len(songs) >= args.size:
            break
        key = artist_key(row["artist"] or "", row["artist_id"])
        if key in seen_artists:
            reject("artist already in set")
            continue
        vocals_path = library / row["id"] / "vocals.mp3"
        if not vocals_path.exists():
            reject("no vocals.mp3")
            continue
        lines = reference_lines(row["synced_lyrics"])
        problem = lrc_problem(lines, row["duration"])
        if problem:
            reject(problem)
            continue
        activity, audio_seconds = onset_activity(
            vocals_path, [l["start"] for l in lines]
        )
        if activity < MIN_ONSET_ACTIVITY:
            reject("line starts miss the singing")
            continue
        if lines[-1]["start"] >= audio_seconds:
            reject("lines past the end of the song")
            continue

        language = normalize_language(row["language"])
        language_source = "db"
        if not language:
            detected = detect_vocals_language(row["id"], vocals_path)
            if not detected:
                reject("language detection failed")
                continue
            language, language_source = detected["language"], "detected"

        seen_artists.add(key)
        songs.append(
            TestSong(
                song_id=row["id"],
                title=row["title"],
                artist=row["artist"],
                artist_key=key,
                language=language,
                language_source=language_source,
                duration=round(audio_seconds, 2),
                vocals_path=str(vocals_path),
                synced_lyrics=row["synced_lyrics"],
                onset_activity=round(activity, 3),
            )
        )
        logger.info(
            "%3d  %s — %s [%s]", len(songs), row["artist"], row["title"], language
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    TESTSET_PATH.write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "seed": args.seed,
                "candidates": len(rows),
                "rejected": rejected,
                "songs": songs,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    languages: dict[str, int] = {}
    for song in songs:
        languages[song["language"]] = languages.get(song["language"], 0) + 1
    logger.info("\nWrote %d songs to %s", len(songs), TESTSET_PATH)
    logger.info("Languages: %s", languages)
    logger.info("Rejected: %s", rejected)


if __name__ == "__main__":
    main()
