"""
Word timing experiments, compared by ear on the admin Compare word timing page.

An experiment script (backend/scripts/experiments/align_on_mix.py is the
first) aligns songs two ways, A and B, and writes the results to a folder
under EXPERIMENTS_DIR:

    <experiment>/meta.json            {"name", "description", "a": {"key", "label"}, "b": {...},
                                       "groups": [{"key", "label"}, ...] in the order to check them,
                                       "compareEnds": true to also list lines whose words end
                                       elsewhere (optional; starts only by default)}
    <experiment>/results/<song>.json  {"id", "title", "artist", "group",
                                       <a key>: {"words", "mean_score", "bad", "lines"}, <b key>: ...}
    <experiment>/answers.json         written here: {song_id: {moment key: answer}}

An experiment's timings never reach the TV. The folder is gitignored, so
experiments exist only where they were run.

One experiment comes from the database instead of a folder: the songs the
LRC offset sweep job found off, waiting for Apply shifts
(services/lrc_offset_layer.py LrcOffsetReview). It keeps its answers on each
song, so it works on prod too.
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

_BACKEND_DIR = Path(__file__).resolve().parents[2]
EXPERIMENTS_DIR = Path(
    os.environ.get(
        "WORD_TIMING_EXPERIMENTS_DIR",
        _BACKEND_DIR / "scripts" / "experiments" / "word_timing" / "results",
    )
)

# A line is worth a listen when its words start this far apart on average (s).
MIN_MEAN_SHIFT_SECONDS = 0.25

ANSWERS = ("b_right", "a_right", "both_wrong", "cant_tell")

_SONG_ID = re.compile(r"^[0-9a-f-]{36}$")


class NotFound(Exception):
    pass


class BadAnswer(Exception):
    pass


def _experiment_dir(experiment_id: str) -> Path:
    """The folder of an experiment that exists; never a path outside EXPERIMENTS_DIR."""
    for path in _experiment_dirs():
        if path.name == experiment_id:
            return path
    raise NotFound(f"No experiment {experiment_id!r}")


def _experiment_dirs() -> list[Path]:
    if not EXPERIMENTS_DIR.is_dir():
        return []
    return sorted(p for p in EXPERIMENTS_DIR.iterdir() if (p / "meta.json").is_file())


def _meta(path: Path) -> dict:
    meta = json.loads((path / "meta.json").read_text())
    return {
        "id": path.name,
        "name": meta["name"],
        "description": meta.get("description", ""),
        "a": meta["a"],
        "b": meta["b"],
        "groups": meta.get("groups", []),
        "compareEnds": bool(meta.get("compareEnds", False)),
    }


def _result(path: Path, song_id: str) -> dict:
    if not _SONG_ID.match(song_id):
        raise NotFound(f"No song {song_id!r}")
    file = path / "results" / f"{song_id}.json"
    if not file.is_file():
        raise NotFound(f"No song {song_id!r} in this experiment")
    return json.loads(file.read_text())


def _results(path: Path) -> list[dict]:
    folder = path / "results"
    if not folder.is_dir():
        return []
    return [json.loads(f.read_text()) for f in sorted(folder.glob("*.json"))]


def _answers(path: Path) -> dict[str, dict[str, str]]:
    file = path / "answers.json"
    return json.loads(file.read_text()) if file.is_file() else {}


def _by_line(words: list[dict]) -> dict[int, list[dict]]:
    lines: dict[int, list[dict]] = defaultdict(list)
    for word in words:
        lines[word["line_index"]].append(word)
    return lines


def _word_shift(x: dict, y: dict, compare_ends: bool) -> float:
    shift = abs(x["start"] - y["start"])
    return max(shift, abs(x["end"] - y["end"])) if compare_ends else shift


def moments(
    a_words: list[dict], b_words: list[dict], compare_ends: bool = False
) -> list[dict]:
    """The lines whose timing differs enough to hear, in song order.

    Words are matched by position in the line; a line with a different word
    count on each side always differs. With `compare_ends`, a word that ends
    elsewhere counts as much as one that starts elsewhere (an experiment that
    cuts held words changes only ends).
    """
    a_lines, b_lines = _by_line(a_words), _by_line(b_words)
    found = []
    for line_index in sorted(set(a_lines) | set(b_lines)):
        a, b = a_lines.get(line_index, []), b_lines.get(line_index, [])
        if a and b and len(a) == len(b):
            shift = sum(_word_shift(x, y, compare_ends) for x, y in zip(a, b)) / len(a)
            if shift < MIN_MEAN_SHIFT_SECONDS:
                continue
        else:
            shift = None
        both = a + b
        found.append(
            {
                "key": f"line:{line_index}",
                "lineIndex": line_index,
                "start": min(w["start"] for w in both),
                "end": max(w["end"] for w in both),
                "meanShift": round(shift, 2) if shift is not None else None,
                "a": a,
                "b": b,
            }
        )
    return found


class _FolderExperiment:
    """An experiment a script wrote to a folder under EXPERIMENTS_DIR."""

    def __init__(self, path: Path):
        self.path = path

    def meta(self) -> dict:
        return _meta(self.path)

    def results(self) -> list[dict]:
        return _results(self.path)

    def result(self, song_id: str) -> dict:
        return _result(self.path, song_id)

    def answers(self) -> dict[str, dict[str, str]]:
        return _answers(self.path)

    def write_song_answers(self, song_id: str, song_answers: dict[str, str]) -> None:
        answers = _answers(self.path)
        answers[song_id] = song_answers
        file = self.path / "answers.json"
        tmp = file.with_suffix(".tmp")
        tmp.write_text(json.dumps(answers, indent=1))
        tmp.replace(file)


def _experiment(experiment_id: str, session: Session | None):
    from app.services.lrc_offset_layer import REVIEW_ID, LrcOffsetReview

    if experiment_id == REVIEW_ID and session is not None:
        return _CheckedResult(LrcOffsetReview(session))
    return _FolderExperiment(_experiment_dir(experiment_id))


class _CheckedResult:
    """A database experiment, with a missing song raised as NotFound."""

    def __init__(self, inner):
        self.inner = inner

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def result(self, song_id: str) -> dict:
        if not _SONG_ID.match(song_id):
            raise NotFound(f"No song {song_id!r}")
        found = self.inner.result(song_id)
        if found is None:
            raise NotFound(f"No song {song_id!r} in this experiment")
        return found


def _side(result: dict, key: str) -> dict | None:
    side = result.get(key)
    return side if side and side.get("words") is not None else None


def list_experiments(session: Session | None = None) -> list[dict]:
    from app.services.lrc_offset_layer import LrcOffsetReview

    found = [_meta(path) for path in _experiment_dirs()]
    if session is not None:
        found.append(LrcOffsetReview(session).meta())
    return found


def list_songs(experiment_id: str, session: Session | None = None) -> dict:
    """The experiment and its songs, with how many moments each has to check.

    Songs still to check come first, then by group as the script wrote them
    (the songs it should help before the controls), then the most moments.
    """
    experiment = _experiment(experiment_id, session)
    meta = experiment.meta()
    answers = experiment.answers()
    rows = []
    tally: dict[str, int] = defaultdict(int)
    for result in experiment.results():
        a, b = _side(result, meta["a"]["key"]), _side(result, meta["b"]["key"])
        if not a or not b:
            continue
        keys = {m["key"] for m in moments(a["words"], b["words"], meta["compareEnds"])}
        song_answers = {
            k: v for k, v in answers.get(result["id"], {}).items() if k in keys
        }
        for answer in song_answers.values():
            tally[answer] += 1
        rows.append(
            {
                "songId": result["id"],
                "title": result["title"],
                "artist": result["artist"],
                "group": result.get("group"),
                "a": {
                    "bad": a.get("bad"),
                    "lines": a.get("lines"),
                    "meanScore": a.get("mean_score"),
                },
                "b": {
                    "bad": b.get("bad"),
                    "lines": b.get("lines"),
                    "meanScore": b.get("mean_score"),
                },
                "moments": len(keys),
                "answered": len(song_answers),
            }
        )
    order = {g["key"]: i for i, g in enumerate(meta["groups"])}
    rows.sort(
        key=lambda r: (
            r["moments"] == 0 or r["answered"] >= r["moments"],
            order.get(r["group"], len(order)),
            -r["moments"],
            r["title"].lower(),
        )
    )
    return {"experiment": meta, "songs": rows, "tally": dict(tally)}


def song_detail(
    experiment_id: str, song_id: str, session: Session | None = None
) -> dict:
    experiment = _experiment(experiment_id, session)
    meta = experiment.meta()
    result = experiment.result(song_id)
    a, b = _side(result, meta["a"]["key"]), _side(result, meta["b"]["key"])
    if not a or not b:
        raise NotFound("This song failed to align one of the two ways")
    song_answers = experiment.answers().get(song_id, {})
    found = moments(a["words"], b["words"], meta["compareEnds"])
    for moment in found:
        moment["answer"] = song_answers.get(moment["key"])
    return {
        "songId": song_id,
        "title": result["title"],
        "artist": result["artist"],
        "group": result.get("group"),
        "moments": found,
    }


def save_answers(
    experiment_id: str,
    song_id: str,
    items: list[dict[str, Any]],
    session: Session | None = None,
) -> None:
    """Save answers by moment key; an answer of None clears it. All or nothing."""
    experiment = _experiment(experiment_id, session)
    keys = {m["key"] for m in song_detail(experiment_id, song_id, session)["moments"]}
    for item in items:
        if item["key"] not in keys:
            raise BadAnswer(f"No moment {item['key']!r} in this song")
        if item["answer"] is not None and item["answer"] not in ANSWERS:
            raise BadAnswer(f"Unknown answer {item['answer']!r}")
    song_answers = dict(experiment.answers().get(song_id, {}))
    for item in items:
        if item["answer"] is None:
            song_answers.pop(item["key"], None)
        else:
            song_answers[item["key"]] = item["answer"]
    experiment.write_song_answers(song_id, song_answers)
