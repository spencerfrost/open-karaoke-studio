"""
Vocal range ear checks, for the admin Check vocal range page.

The vocal range benchmark (backend/scripts/experiments/vocal_range/) writes its
results to RESULTS_DIR:

    testset.json          {"songs": [{"song_id", "title", "artist", "picked_as",
                           "stored_low", "stored_high", ...}]}
    runs/<method>.json    {"method", "setting", "description",
                           "results": {song_id: {"low", "high", "label",
                                                  "low_moments", "high_moments"}}}
    contours/<setting>/<song_id>.npz   the pitch track each method read
    answers.json          written here: {song_id: {key: answer}}

and its reference set beside the folder (reference.json).

A moment is a stretch of the lead stem a method says sets one end of the
range: a note and where it is sung. A method gives up to three per end,
longest first; the first ("primary") decides the end, the others stand in
when the first can't be told by ear, so only primaries count as to-check. Its key is the note and start time, so two
methods pointing at the same moment share one answer, and a method that
moves it gets a fresh listen. The song's kind (sung, rapped...) is answered
under the key "kind".

Nothing here touches the database: the benchmark never reaches the TV. The
folder is gitignored, so results exist only where the benchmark was run.
"""

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

import numpy as np

_BACKEND_DIR = Path(__file__).resolve().parents[2]
RESULTS_DIR = Path(
    os.environ.get(
        "VOCAL_RANGE_RESULTS_DIR",
        _BACKEND_DIR / "scripts" / "experiments" / "vocal_range" / "results",
    )
)

MOMENT_ANSWERS = (
    "right",
    "octave_high",  # the note shown is an octave above what's sung
    "octave_low",  # the note shown is an octave below what's sung
    "wrong_note",
    "not_singer",  # bleed, an effect, backing, an instrument
    "no_note",  # the singer, but rapping or speaking: no note to judge
    "screamed",  # the singer screaming or yelling: no clear note
    "cant_tell",
)
KIND_ANSWERS = ("sung", "mixed", "rapped", "spoken", "instrumental")
KIND_KEY = "kind"

# Test-set groups, in the order to check them.
GROUPS = (
    ("named", "Plan's test songs"),
    ("widest", "Widest stored ranges"),
    ("wide", "Wide"),
    ("narrow", "Narrow"),
    ("typical", "Typical"),
    ("unmeasured", "Not measured before"),
)
_GROUP_ORDER = {key: i for i, (key, _) in enumerate(GROUPS)}

# Pitch track shown around a moment.
CONTOUR_PAD_SECONDS = 2.0
# A frame is drawn as confident above this voiced probability (the method's own cut).
CONFIDENT_PROBABILITY = 0.75

_LETTER = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


class NotFound(Exception):
    pass


class BadAnswer(Exception):
    pass


def note_to_midi(note: str) -> int:
    note = note.strip().replace("♯", "#").replace("♭", "b")
    letter, rest = note[0].upper(), note[1:]
    shift = 0
    while rest and rest[0] in "#b":
        shift += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return _LETTER[letter] + shift + 12 * (int(rest) + 1)


def moment_key(note: str, start: float) -> str:
    return f"{note}@{start:.2f}"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text()) if path.is_file() else None


def _testset() -> list[dict]:
    data = _read_json(RESULTS_DIR / "testset.json")
    return data["songs"] if data else []


def _runs(methods: Optional[list[str]] = None) -> list[dict]:
    """Every method's run (or only `methods`), baseline first, then by name."""
    folder = RESULTS_DIR / "runs"
    if not folder.is_dir():
        return []
    runs = [json.loads(f.read_text()) for f in sorted(folder.glob("*.json"))]
    if methods is not None:
        runs = [r for r in runs if r["method"] in methods]
    runs.sort(key=lambda r: (r["method"] != "baseline", r["method"]))
    return runs


def _reference() -> dict[str, dict]:
    data = _read_json(RESULTS_DIR.parent / "reference.json") or {}
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _answers() -> dict[str, dict[str, str]]:
    return _read_json(RESULTS_DIR / "answers.json") or {}


def _song(song_id: str) -> dict:
    for song in _testset():
        if song["song_id"] == song_id:
            return song
    raise NotFound(f"No song {song_id!r} in the test set")


def _moments(song_id: str, runs: list[dict]) -> list[dict]:
    """The song's moments across every method, each once: those setting a
    lowest note first, then a highest; within each, the longest first (rank
    0, the one that decides that end), then in song order."""
    found: dict[str, dict] = {}
    for run in runs:
        result = run["results"].get(song_id)
        if not result:
            continue
        for end in ("low", "high"):
            note = result.get(end)
            if note is None:
                continue
            for rank, m in enumerate(result.get(f"{end}_moments") or []):
                key = moment_key(note, m["start"])
                moment = found.setdefault(
                    key,
                    {
                        "key": key,
                        "note": note,
                        "midi": note_to_midi(note),
                        "start": m["start"],
                        "duration": m["duration"],
                        "setting": run["setting"],
                        "sets": [],
                    },
                )
                moment["sets"].append(
                    {"method": run["method"], "end": end, "rank": rank}
                )

    for moment in found.values():
        moment["primary"] = min(s["rank"] for s in moment["sets"]) == 0

    def order(moment: dict) -> tuple:
        ends = [0 if s["end"] == "low" else 1 for s in moment["sets"]]
        return (min(ends), min(s["rank"] for s in moment["sets"]), moment["start"])

    return sorted(found.values(), key=order)


def _contour_excerpt(
    setting: str, song_id: str, start: float, end: float
) -> Optional[dict]:
    """The voiced frames of the pitch track between `start` and `end`."""
    path = RESULTS_DIR / "contours" / setting / f"{song_id}.npz"
    if not path.is_file():
        return None
    data = np.load(path)
    times, f0, prob = data["times"], data["f0"], data["voiced_prob"]
    window = (times >= start) & (times <= end) & ~np.isnan(f0)
    with np.errstate(divide="ignore", invalid="ignore"):
        midi = 69 + 12 * np.log2(f0[window] / 440.0)
    return {
        "start": round(start, 2),
        "end": round(end, 2),
        "points": [
            [round(float(t), 2), round(float(m), 2), int(p > CONFIDENT_PROBABILITY)]
            for t, m, p in zip(times[window], midi, prob[window])
        ],
    }


def _end_verdicts(
    song_id: str, run: dict, answers: dict[str, str]
) -> dict[str, Optional[str]]:
    """Each end's verdict for one method: the answer to its first answered moment."""
    result = run["results"].get(song_id) or {}
    verdicts: dict[str, Optional[str]] = {}
    for end in ("low", "high"):
        note = result.get(end)
        verdicts[end] = None
        if note is None:
            continue
        for m in result.get(f"{end}_moments") or []:
            answer = answers.get(moment_key(note, m["start"]))
            if answer and answer != "cant_tell":
                verdicts[end] = answer
                break
    return verdicts


def _method_summary(run: dict) -> dict:
    return {
        "method": run["method"],
        "setting": run["setting"],
        "description": run.get("description", ""),
    }


def _result_summary(result: Optional[dict]) -> Optional[dict]:
    if result is None:
        return None
    return {
        "low": result.get("low"),
        "high": result.get("high"),
        "label": result.get("label"),
    }


def list_songs(methods: Optional[list[str]] = None) -> dict:
    """Every test song with each method's range and how many of its primary
    moments are answered, plus each method's verdicts so far. Songs still to
    check come first, then by group. `methods` narrows the moments counted
    (and the ranges listed) to those methods; `allMethods` lists every run."""
    all_runs = _runs()
    runs = _runs(methods)
    answers = _answers()
    reference = _reference()
    verdicts: dict[str, dict[str, int]] = {
        run["method"]: defaultdict(int) for run in runs
    }
    kinds: dict[str, int] = defaultdict(int)
    rows = []
    for song in _testset():
        song_id = song["song_id"]
        song_answers = answers.get(song_id, {})
        keys = {m["key"] for m in _moments(song_id, runs) if m["primary"]}
        answered = sum(1 for k in keys if k in song_answers)
        kind = song_answers.get(KIND_KEY)
        if kind:
            kinds[kind] += 1
        for run in runs:
            for verdict in _end_verdicts(song_id, run, song_answers).values():
                if verdict:
                    verdicts[run["method"]][verdict] += 1
        rows.append(
            {
                "songId": song_id,
                "title": song["title"],
                "artist": song["artist"],
                "group": song["picked_as"],
                "stored": (
                    {"low": song["stored_low"], "high": song["stored_high"]}
                    if song.get("stored_low")
                    else None
                ),
                "results": {
                    run["method"]: _result_summary(run["results"].get(song_id))
                    for run in runs
                },
                "moments": len(keys),
                "answered": answered,
                "kind": kind,
                "referenceKind": reference.get(song_id, {}).get("kind"),
            }
        )
    rows.sort(
        key=lambda r: (
            r["answered"] >= r["moments"] and r["kind"] is not None,
            _GROUP_ORDER.get(r["group"], len(_GROUP_ORDER)),
            r["title"].lower(),
        )
    )
    return {
        "methods": [_method_summary(run) for run in runs],
        "allMethods": [_method_summary(run) for run in all_runs],
        "groups": [{"key": k, "label": label} for k, label in GROUPS],
        "songs": rows,
        "verdicts": {method: dict(v) for method, v in verdicts.items()},
        "kinds": dict(kinds),
    }


def song_detail(song_id: str, methods: Optional[list[str]] = None) -> dict:
    song = _song(song_id)
    runs = _runs(methods)
    song_answers = _answers().get(song_id, {})
    moments = _moments(song_id, runs)
    for moment in moments:
        moment["answer"] = song_answers.get(moment["key"])
        moment["contour"] = _contour_excerpt(
            moment["setting"],
            song_id,
            moment["start"] - CONTOUR_PAD_SECONDS,
            moment["start"] + moment["duration"] + CONTOUR_PAD_SECONDS,
        )
    reference = _reference().get(song_id)
    return {
        "songId": song_id,
        "title": song["title"],
        "artist": song["artist"],
        "group": song["picked_as"],
        "stored": (
            {"low": song["stored_low"], "high": song["stored_high"]}
            if song.get("stored_low")
            else None
        ),
        "reference": reference,
        "kind": song_answers.get(KIND_KEY),
        "methods": [
            {
                **_method_summary(run),
                "result": _result_summary(run["results"].get(song_id)),
                "verdicts": _end_verdicts(song_id, run, song_answers),
            }
            for run in runs
        ],
        "moments": moments,
    }


def save_answers(song_id: str, items: list[dict[str, Any]]) -> None:
    """Save answers by key ("kind" or any method's moment key); None clears
    one. All or nothing."""
    keys = {m["key"] for m in _moments(_song(song_id)["song_id"], _runs())}
    for item in items:
        key, answer = item["key"], item["answer"]
        if key == KIND_KEY:
            allowed: tuple[str, ...] = KIND_ANSWERS
        elif key in keys:
            allowed = MOMENT_ANSWERS
        else:
            raise BadAnswer(f"No moment {key!r} in this song")
        if answer is not None and answer not in allowed:
            raise BadAnswer(f"Unknown answer {answer!r} for {key!r}")
    answers = _answers()
    song_answers = answers.setdefault(song_id, {})
    for item in items:
        if item["answer"] is None:
            song_answers.pop(item["key"], None)
        else:
            song_answers[item["key"]] = item["answer"]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    file = RESULTS_DIR / "answers.json"
    tmp = file.with_suffix(".tmp")
    tmp.write_text(json.dumps(answers, indent=1, ensure_ascii=False))
    tmp.replace(file)
