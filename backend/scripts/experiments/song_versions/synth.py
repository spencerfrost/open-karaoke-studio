"""
Make synthetic versions of the control songs, with a known answer.

Each recipe cuts and pastes a control's vocal stems (lead, and backing when
there is one) into a new version and moves the control's line times with the
edit, so the truth is exact as far as today's timing of the control is right
(controls are picked for that). Only the vocal stems are written: alignment,
transcription and the singing map listen to nothing else.

Recipes:
  new_intro     ~30 s of another control's singing put in front (words the
                album lyrics lack), then 2 s of silence
  extra_chorus  four lines from the middle sung twice
  cut_verse     four lines from the first third left out
  long_outro    a minute of silence after the last line
  intro_outro   new_intro + long_outro: the Terrible Lie shape

    python scripts/experiments/song_versions/synth.py              # adds them to the test set
    python scripts/experiments/song_versions/synth.py --force      # rebuild them

Writes results/synthetic/<id>/{vocals,backing_vocals}.mp3 and adds the songs
to results/testset.json with kind "synthetic" and their truth lines.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from common import (
    SYNTHETIC_DIR,
    TESTSET_PATH,
    TestSong,
    TruthLine,
    album_lines,
    load_testset,
)

from app.services.singing_map import measure_singing_map  # noqa: E402

SAMPLE_RATE = 44100
EDGE = 0.3  # cuts fall this far before a line's first word
INTRO_SECONDS = 30.0
INTRO_GAP = 2.0
OUTRO_SECONDS = 60.0
BLOCK_LINES = 4
STEMS = ("vocals.mp3", "backing_vocals.mp3")


@dataclass
class Version:
    """A version being built: its stems and its truth, edited together."""

    stems: dict[str, np.ndarray]
    truth: list[TruthLine]

    @property
    def length(self) -> float:
        return max(len(a) for a in self.stems.values()) / SAMPLE_RATE


def _load(song: TestSong) -> Version:
    import librosa

    stems = {}
    for name in STEMS:
        path = Path(song["song_dir"]) / name
        if path.exists():
            stems[name], _ = librosa.load(str(path), sr=SAMPLE_RATE, mono=True)
    return Version(stems=stems, truth=_truth(song))


def _truth(song: TestSong) -> list[TruthLine]:
    """The control's lines where today's timing says they're sung."""
    lines = album_lines(song["album_lrc"])
    by_lrc_index = {line["lrc_index"]: line for line in lines}
    starts: dict[int, float] = {}
    for word in (song["today"] or {}).get("words", []):
        line = by_lrc_index.get(word["line_index"])
        if line is not None and line["index"] not in starts:
            starts[line["index"]] = word["start"]
    return [
        TruthLine(
            start=round(starts[line["index"]], 3),
            text=line["text"],
            source="album",
            album_index=line["index"],
        )
        for line in lines
        if line["index"] in starts
    ]


def _cut(audio: np.ndarray, a: float, b: float) -> np.ndarray:
    return audio[int(a * SAMPLE_RATE) : int(b * SAMPLE_RATE)]


def _silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SAMPLE_RATE), dtype=np.float32)


def _block(version: Version, at: float) -> tuple[int, float, float]:
    """BLOCK_LINES lines starting at fraction `at` of the song: (first, start, end)."""
    first = min(int(len(version.truth) * at), len(version.truth) - BLOCK_LINES - 1)
    start = version.truth[first]["start"] - EDGE
    end = version.truth[first + BLOCK_LINES]["start"] - EDGE
    return first, start, end


def new_intro(version: Version, donor: Version) -> Version:
    d0 = donor.truth[0]["start"] - EDGE
    d1 = d0 + INTRO_SECONDS
    kept = [t for t in donor.truth if t["start"] < d1 - 1.0]
    if kept:
        d1 = min(d1, max(t["start"] for t in kept) + 6.0)
    shift = d1 - d0 + INTRO_GAP
    stems = {}
    for name, audio in version.stems.items():
        donor_audio = donor.stems.get(name)
        intro = (
            _cut(donor_audio, d0, d1) if donor_audio is not None else _silence(d1 - d0)
        )
        stems[name] = np.concatenate([intro, _silence(INTRO_GAP), audio])
    truth = [
        TruthLine(
            start=round(t["start"] - d0, 3),
            text=t["text"],
            source="heard",
            album_index=None,
        )
        for t in kept
    ] + [{**t, "start": round(t["start"] + shift, 3)} for t in version.truth]
    return Version(stems=stems, truth=truth)


def extra_chorus(version: Version) -> Version:
    first, a, b = _block(version, 0.5)
    stems = {
        name: np.concatenate(
            [_cut(audio, 0, b), _cut(audio, a, b), audio[int(b * SAMPLE_RATE) :]]
        )
        for name, audio in version.stems.items()
    }
    shift = b - a
    block = version.truth[first : first + BLOCK_LINES]
    truth = (
        version.truth[: first + BLOCK_LINES]
        + [{**t, "start": round(t["start"] + shift, 3)} for t in block]
        + [
            {**t, "start": round(t["start"] + shift, 3)}
            for t in version.truth[first + BLOCK_LINES :]
        ]
    )
    return Version(stems=stems, truth=truth)


def cut_verse(version: Version) -> Version:
    first, a, b = _block(version, 0.3)
    stems = {
        name: np.concatenate([_cut(audio, 0, a), audio[int(b * SAMPLE_RATE) :]])
        for name, audio in version.stems.items()
    }
    shift = b - a
    truth = version.truth[:first] + [
        {**t, "start": round(t["start"] - shift, 3)}
        for t in version.truth[first + BLOCK_LINES :]
    ]
    return Version(stems=stems, truth=truth)


def long_outro(version: Version) -> Version:
    stems = {
        name: np.concatenate([audio, _silence(OUTRO_SECONDS)])
        for name, audio in version.stems.items()
    }
    return Version(stems=stems, truth=list(version.truth))


RECIPES: dict[str, Callable[[Version, Version], Version]] = {
    "new_intro": new_intro,
    "extra_chorus": lambda v, _: extra_chorus(v),
    "cut_verse": lambda v, _: cut_verse(v),
    "long_outro": lambda v, _: long_outro(v),
    "intro_outro": lambda v, d: long_outro(new_intro(v, d)),
}


def _write(version: Version, folder: Path) -> None:
    import soundfile as sf

    folder.mkdir(parents=True, exist_ok=True)
    for name, audio in version.stems.items():
        with tempfile.NamedTemporaryFile(suffix=".wav") as wav:
            sf.write(wav.name, audio, SAMPLE_RATE)
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loglevel",
                    "error",
                    "-i",
                    wav.name,
                    "-q:a",
                    "2",
                    str(folder / name),
                ],
                check=True,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[1])
    parser.add_argument("--recipes", nargs="*", default=list(RECIPES))
    parser.add_argument("--sources", type=int, default=4, help="controls per recipe")
    parser.add_argument("--force", action="store_true", help="rebuild existing ones")
    args = parser.parse_args()

    songs = load_testset()
    controls = [s for s in songs if s["kind"] == "control" and s["today"]]
    if len(controls) < 2:
        raise SystemExit("Need at least two controls with stored timing")
    existing = {s["song_id"] for s in songs if s["kind"] == "synthetic"}
    loaded: dict[str, Version] = {}

    def version_of(song: TestSong) -> Version:
        if song["song_id"] not in loaded:
            loaded[song["song_id"]] = _load(song)
        return loaded[song["song_id"]]

    added: list[TestSong] = []
    for recipe_index, recipe in enumerate(args.recipes):
        for k in range(min(args.sources, len(controls))):
            # Each recipe takes a different run of controls; the donor is the next one.
            source = controls[(recipe_index * args.sources + k) % len(controls)]
            donor = controls[(recipe_index * args.sources + k + 1) % len(controls)]
            song_id = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"{source['song_id']}/{recipe}")
            )
            if song_id in existing and not args.force:
                continue
            base = version_of(source)
            if len(base.truth) < 2 * BLOCK_LINES + 2:
                continue
            built = RECIPES[recipe](base, version_of(donor))
            folder = SYNTHETIC_DIR / song_id
            _write(built, folder)
            singing_map = measure_singing_map(folder)
            added.append(
                TestSong(
                    song_id=song_id,
                    kind="synthetic",
                    picked_as=recipe,
                    title=f"{source['title']} [{recipe}]",
                    artist=source["artist"],
                    duration=round(built.length, 2),
                    song_dir=str(folder),
                    language=source["language"],
                    language_source=source["language_source"],
                    album_lrc=source["album_lrc"],
                    album_from=source["song_id"],
                    pair_ids=[],
                    today=None,
                    lead=[tuple(i) for i in singing_map["lead"]],
                    backing=(
                        None
                        if singing_map["backing"] is None
                        else [tuple(i) for i in singing_map["backing"]]
                    ),
                    truth=built.truth,
                    untimed_before=None,
                    untimed_after=None,
                )
            )
            print(
                f"{recipe}: {source['artist']} - {source['title']} ({built.length:.0f}s)"
            )

    replaced = {s["song_id"] for s in added}
    data = json.loads(TESTSET_PATH.read_text())
    data["songs"] = [s for s in data["songs"] if s["song_id"] not in replaced] + added
    TESTSET_PATH.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print(f"Added {len(added)} synthetic songs to {TESTSET_PATH}")


if __name__ == "__main__":
    main()
