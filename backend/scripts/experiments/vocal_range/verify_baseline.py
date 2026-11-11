"""Check that the harness baseline gives exactly what production gives.

Runs app/services/vocal_range_child.py (the production child) on a few test
songs and compares with methods.frame_percentiles on the cached contour. A
mismatch means the harness isn't measuring today's method.

Usage (from backend/, venv active):
    python scripts/experiments/vocal_range/verify_baseline.py [--count 3]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from common import load_contour, load_testset
from methods import frame_percentiles

from app.services.audio import _run_vocal_range_child  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--count", type=int, default=3)
    args = parser.parse_args()

    checked = mismatched = 0
    for song in load_testset():
        if checked == args.count:
            break
        contour = load_contour("pyin", song["song_id"])
        if contour is None:
            continue
        harness = frame_percentiles(contour, song)
        child = _run_vocal_range_child(Path(song["vocals_path"]))
        same = (harness.low, harness.high) == (child["low"], child["high"])
        mismatched += not same
        checked += 1
        print(
            f"{'ok  ' if same else 'DIFF'} harness {harness.low}–{harness.high}  "
            f"child {child['low']}–{child['high']}  {song['artist']} - {song['title']}"
        )
    if mismatched:
        raise SystemExit(f"{mismatched}/{checked} differ")


if __name__ == "__main__":
    main()
