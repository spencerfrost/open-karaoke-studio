"""
Add a by-ear transcription of part of a real version as its answer key.

The transcription is a text file, one sung line per line, each starting with
its time: "0:34 I can smash myself to pieces". It becomes the song's truth for
the stretch it covers (`truth_span`), which score.py judges every run on.

It also builds the version's own lyrics (`version_lrc`): the transcribed lines,
then the body lines from another song's LRC (usually the album version's)
moved by --body-shift. run.py --lyrics version runs methods on them. The
body's times are only a starting point, not truth.

    python scripts/experiments/song_versions/add_version_lyrics.py a741eb92-... \\
        results/version_lyrics/a741eb92-....txt --body-from aafb2b4b-... --body-shift 151

Writes only results/testset.json.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common import TESTSET_PATH, TruthLine, album_lines

from app.services.lyrics_retiming import _format_timestamp  # noqa: E402

_LINE = re.compile(r"^\s*(\d+):(\d{1,2}(?:\.\d+)?)\s+(.+?)\s*$")
# The truth span runs this long past the last transcribed line's start.
SPAN_TAIL_SECONDS = 9.0


def parse(path: Path) -> list[tuple[float, str]]:
    lines = []
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        if not raw.strip():
            continue
        match = _LINE.match(raw)
        if not match:
            raise SystemExit(f"{path}:{number}: expected 'm:ss text', got {raw!r}")
        minutes, seconds, text = match.groups()
        lines.append((int(minutes) * 60 + float(seconds), text))
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[1])
    parser.add_argument("song_id")
    parser.add_argument("transcription", type=Path)
    parser.add_argument("--body-from", required=True, help="song whose LRC is the body")
    parser.add_argument("--body-shift", type=float, required=True, help="seconds")
    args = parser.parse_args()

    data = json.loads(TESTSET_PATH.read_text())
    by_id = {s["song_id"]: s for s in data["songs"]}
    if args.song_id not in by_id:
        raise SystemExit(f"{args.song_id} is not in the test set")
    if args.body_from not in by_id:
        raise SystemExit(f"{args.body_from} is not in the test set")
    song = by_id[args.song_id]
    heard = parse(args.transcription)
    body = album_lines(by_id[args.body_from]["album_lrc"])

    song["truth"] = [
        TruthLine(start=start, text=text, source="heard", album_index=None)
        for start, text in heard
    ]
    song["truth_span"] = [0.0, heard[-1][0] + SPAN_TAIL_SECONDS]
    song["version_lrc"] = "\n".join(
        [f"{_format_timestamp(start)}{text}" for start, text in heard]
        + [
            f"{_format_timestamp(line['time'] + args.body_shift)}{line['text']}"
            for line in body
        ]
    )
    song["version_lyrics_from"] = {
        "transcription": str(args.transcription),
        "body_from": args.body_from,
        "body_shift": args.body_shift,
    }
    TESTSET_PATH.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print(
        f"{song['artist']} - {song['title']}: {len(heard)} truth lines to "
        f"{song['truth_span'][1]:.0f}s, version lyrics {len(heard) + len(body)} lines"
    )


if __name__ == "__main__":
    main()
