"""
Which songs that pass the alignment gate are still late or early as a whole?

The offset sweep only runs on songs scoring below 0.3, in 0.5 s steps. GRiZ
"Find My Own Way" scores 0.31 with an LRC 0.9 s late, so it's never swept, and
0.9 s falls between the steps anyway. This sweeps every song with synced
lyrics the way the roadmap proposes: ±1.5 s in 0.5 s steps, then 0.1 s steps
around the best, against the lead + backing vocals the aligner hears. Nothing
is written to the database.

Each song's sweep is saved, so a rerun carries on where it stopped. Then the
songs whose best shift gains enough are aligned twice with the production
aligner, unshifted and shifted, for the admin Compare word timing page:

- clear: the shift passes the production gate with a gain of twice the gate
  or more;
- borderline: it passes, by less than that, the songs most likely to be
  noise;
- under: the largest gains just under the gate, to hear whether the gate,
  measured with 0.5 s steps, still fits a sweep with more shifts to pick from.

Export the songs first (read-only), then run from backend/ with the venv:

    psql "$DATABASE_URL" -c "copy (select id, title, artist, language,
        synced_lyrics, singing_map from songs
        where synced_lyrics is not null and synced_lyrics <> '')
        to stdout with (format csv, header)" > songs.csv
    python scripts/experiments/sweep_lrc_offsets.py songs.csv [--limit N] [--under 20]

--only "Find My Own Way" sweeps just the songs whose title contains it, for a
quick look. See docs/plans/2026-10-28-lyrics-roadmap.md.
"""

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from time import perf_counter
from typing import cast

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from align_on_mix import count_bad  # noqa: E402  (same folder)

from app.services.word_timing_experiments import EXPERIMENTS_DIR  # noqa: E402

csv.field_size_limit(10**9)

EXPERIMENT_ID = "sweep_lrc_offsets"
META = {
    "name": "LRC offset sweep",
    "description": (
        "Every song with synced lyrics swept for a whole-song offset within 1.5 s, in "
        "0.5 s steps and then 0.1 s steps around the best. Each song here is aligned "
        "as its LRC is now and with the sweep's shift applied."
    ),
    "a": {"key": "unshifted", "label": "LRC as it is"},
    "b": {"key": "shifted", "label": "Shifted by the sweep"},
    "groups": [
        {"key": "clear", "label": "Shift passes the gate easily"},
        {"key": "borderline", "label": "Shift only just passes the gate"},
        {"key": "under", "label": "Just under the gate: not shifted today"},
    ],
}

# Songs with a gain at least this share of the gate count as "under".
UNDER_GATE_SHARE = 0.5


def sweep_song(row: dict) -> dict | None:
    from app.services.file_service import FileService
    from app.services.lyrics_offset import (
        OFFSET_SWEEP_FINE_STEP_SECONDS,
        OFFSET_SWEEP_NEAR_MAX_SECONDS,
        OFFSET_SWEEP_STEP_SECONDS,
        sweep_lrc_offset,
    )

    vocals = FileService().get_vocals_path(row["id"], ".mp3")
    if not vocals.exists():
        return None
    started = perf_counter()
    sweep = sweep_lrc_offset(
        row["synced_lyrics"],
        vocals,
        language=row.get("language") or "en",
        max_shift=OFFSET_SWEEP_NEAR_MAX_SECONDS,
        step=OFFSET_SWEEP_STEP_SECONDS,
        fine_step=OFFSET_SWEEP_FINE_STEP_SECONDS,
    )
    if sweep is None:
        return None
    return {
        "id": row["id"],
        "artist": row["artist"],
        "title": row["title"],
        **sweep,
        # JSON keys are strings; keep the shifts readable as numbers.
        "scores": [[shift, score] for shift, score in sorted(sweep["scores"].items())],
        "seconds": round(perf_counter() - started, 1),
    }


def group_of(sweep: dict) -> str | None:
    from app.jobs.lyrics_tasks import MIN_OFFSET_GAIN, _offset_rejection_reason
    from app.services.lyrics_offset import LrcOffsetSweep

    # A saved sweep keeps its scores as a list; the gate reads only the rest.
    reason = _offset_rejection_reason(cast(LrcOffsetSweep, sweep))
    if reason is None:
        return "clear" if sweep["gain"] >= 2 * MIN_OFFSET_GAIN else "borderline"
    if (
        reason == "gain_too_small"
        and sweep["gain"] >= UNDER_GATE_SHARE * MIN_OFFSET_GAIN
    ):
        return "under"
    return None


def compare_song(group: str, row: dict, sweep: dict) -> dict:
    from app.services.file_service import FileService
    from app.services.lyrics_alignment import align_lyrics_to_vocals
    from app.services.lyrics_offset import shift_lrc_timestamps

    vocals = FileService().get_vocals_path(row["id"], ".mp3")
    language = row.get("language") or "en"
    singing_map = json.loads(row["singing_map"]) if row.get("singing_map") else None
    # Shifting moves timestamps only, so both sides keep the same line indexes
    # and the Compare page can match them line for line.
    lrcs = {
        "unshifted": (row["synced_lyrics"], "synced"),
        "shifted": (
            shift_lrc_timestamps(row["synced_lyrics"], sweep["shift"]),
            "offset_corrected",
        ),
    }
    result = {
        "id": row["id"],
        "artist": row["artist"],
        "title": row["title"],
        "group": group,
        "shift": sweep["shift"],
        "gain": sweep["gain"],
    }
    for key, (lrc, mode) in lrcs.items():
        aligned = align_lyrics_to_vocals(
            lrc, vocals, language=language, alignment_mode=mode
        )
        if not aligned:
            result[key] = None
            continue
        bad = count_bad(aligned["words"], singing_map) if singing_map else {}
        result[key] = bad | {
            "mean_score": aligned["mean_score"],
            "words": aligned["words"],
        }
    return result


def summarize(sweeps: list[dict], grouped: dict[str, list[dict]]) -> None:
    print(f"\nswept {len(sweeps)} songs")
    for group in ("clear", "borderline", "under"):
        songs = grouped.get(group, [])
        print(f"\n{group}: {len(songs)} songs")
        for s in sorted(songs, key=lambda s: -s["gain"])[:15]:
            print(
                f"  {s['shift']:+.1f} s  gain {s['gain']:+.3f}"
                f"  score {s['baseline_score']:.2f} -> {s['score']:.2f}"
                f"  {s['artist']} - {s['title']}"
            )
    shifted = grouped.get("clear", []) + grouped.get("borderline", [])
    if shifted:
        earlier = sum(s["shift"] < 0 for s in shifted)
        print(
            f"\nwould shift {len(shifted)} songs ({len(shifted) / len(sweeps):.1%}):"
            f" {earlier} earlier, {len(shifted) - earlier} later"
        )
        below_gate_today = sum(s["baseline_score"] < 0.3 for s in shifted)
        print(f"  {below_gate_today} of them score below 0.3 unshifted")
    timed = [s["seconds"] for s in sweeps if "seconds" in s]
    if timed:
        print(f"\nsweep time: {sum(timed) / len(timed):.1f} s a song on average")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--out-dir", type=Path, default=EXPERIMENTS_DIR / EXPERIMENT_ID)
    parser.add_argument("--under", type=int, default=20)
    parser.add_argument("--limit", type=int, help="sweep at most this many songs")
    parser.add_argument("--only", help="only songs whose title contains this")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    rows = [
        r for r in csv.DictReader(open(args.csv_path)) if r["synced_lyrics"].strip()
    ]
    if args.only:
        rows = [r for r in rows if args.only.lower() in (r["title"] or "").lower()]
    if args.limit:
        rows = rows[: args.limit]
    by_id = {r["id"]: r for r in rows}

    sweeps_dir = args.out_dir / "sweeps"
    results_dir = args.out_dir / "results"
    sweeps_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "meta.json").write_text(json.dumps(META, indent=1))

    sweeps = []
    for i, row in enumerate(rows, 1):
        path = sweeps_dir / f"{row['id']}.json"
        if path.exists():
            sweeps.append(json.loads(path.read_text()))
            continue
        print(f"[{i}/{len(rows)}] sweep {row['artist']} - {row['title']}", flush=True)
        try:
            sweep = sweep_song(row)
        except Exception as error:  # one bad song shouldn't stop the run
            print(f"  failed: {error}", flush=True)
            continue
        if sweep is None:
            print("  no vocals or nothing aligned", flush=True)
            continue
        print(
            f"  best {sweep['shift']:+.1f} s, gain {sweep['gain']:+.3f}"
            f" ({sweep['seconds']:.0f} s)",
            flush=True,
        )
        path.write_text(json.dumps(sweep))
        sweeps.append(sweep)

    grouped: dict[str, list[dict]] = {}
    for sweep in sweeps:
        group = group_of(sweep)
        if group:
            grouped.setdefault(group, []).append(sweep)
    grouped["under"] = sorted(grouped.get("under", []), key=lambda s: -s["gain"])[
        : args.under
    ]

    to_compare = [
        (g, s) for g in ("clear", "borderline", "under") for s in grouped.get(g, [])
    ]
    for i, (group, sweep) in enumerate(to_compare, 1):
        path = results_dir / f"{sweep['id']}.json"
        if path.exists() or sweep["id"] not in by_id:
            continue
        print(
            f"[{i}/{len(to_compare)}] compare {group} {sweep['artist']} - {sweep['title']}",
            flush=True,
        )
        try:
            result = compare_song(group, by_id[sweep["id"]], sweep)
        except Exception as error:
            print(f"  failed: {error}", flush=True)
            continue
        path.write_text(json.dumps(result))

    summarize(sweeps, grouped)


if __name__ == "__main__":
    main()
