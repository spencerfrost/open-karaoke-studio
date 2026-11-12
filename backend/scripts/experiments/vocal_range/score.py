"""Run range methods over the test set and score them.

Writes results/runs/<method>.json (every song's result and moments, read by the
ear-check page) and results/report.md. Scores against reference.json
(published sheet-music ranges) where a song has one. A reference's octave is not trusted (see its
_about), so each end is scored modulo the octave (-6..+5 semitones), and the
width is scored as-is: an end an octave out shows as a width about 12 off.
Every method also gets sanity numbers that need no reference (widths, tops at
C6 or above).

Usage (from backend/, venv active):
    python scripts/experiments/vocal_range/score.py [method ...]
"""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from typing import Optional

from common import (
    RESULTS_DIR,
    Reference,
    TestSong,
    load_contour,
    load_reference,
    load_testset,
    note_to_midi,
)
from methods import METHODS, RangeResult

RUNS_DIR = RESULTS_DIR / "runs"
REPORT_PATH = RESULTS_DIR / "report.md"
OCTAVE_ERROR = 10  # width this far off = one end an octave (or so) out
CLOSE = 2  # semitones off that still count as right
C6 = note_to_midi("C6")


def _pc_err(got: Optional[str], want: Optional[str]) -> Optional[int]:
    """Semitones from `want` to `got`, ignoring the octave: -6..+5."""
    if got is None or want is None:
        return None
    return (note_to_midi(got) - note_to_midi(want) + 6) % 12 - 6


def _ref_width(ref: Reference) -> Optional[int]:
    low, high = ref.get("low"), ref.get("high")
    if not low or not high:
        return None
    return note_to_midi(high) - note_to_midi(low)


def _width(r: RangeResult) -> Optional[int]:
    if r.low is None or r.high is None:
        return None
    return note_to_midi(r.high) - note_to_midi(r.low)


def run_method(name: str, songs: list[TestSong]) -> dict[str, RangeResult]:
    setting, fn = METHODS[name]
    results: dict[str, RangeResult] = {}
    for song in songs:
        contour = load_contour(setting, song["song_id"])
        if contour is None:
            continue
        results[song["song_id"]] = fn(contour, song)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / f"{name}.json").write_text(
        json.dumps(
            {
                "method": name,
                "setting": setting,
                "description": (fn.__doc__ or "").strip().split("\n")[0],
                "results": {k: v.to_json() for k, v in results.items()},
            },
            indent=1,
            ensure_ascii=False,
        )
    )
    return results


def summary(results: dict[str, RangeResult], refs: dict[str, Reference]) -> list[str]:
    widths = [w for r in results.values() if (w := _width(r)) is not None]
    tops = sum(
        1 for r in results.values() if r.high is not None and note_to_midi(r.high) >= C6
    )
    no_range = sum(1 for r in results.values() if r.low is None)
    labelled = sum(1 for r in results.values() if r.label)

    low_errs, high_errs, width_errs = [], [], []
    kinds_right = kinds_total = 0
    for song_id, ref in refs.items():
        r = results.get(song_id)
        if r is None:
            continue
        kind = ref.get("kind", "sung")
        if kind in ("rapped", "instrumental", "spoken"):
            kinds_total += 1
            kinds_right += r.label == kind or (kind == "instrumental" and r.low is None)
            continue
        if (e := _pc_err(r.low, ref.get("low"))) is not None:
            low_errs.append(e)
        if (e := _pc_err(r.high, ref.get("high"))) is not None:
            high_errs.append(e)
        rw, mw = _ref_width(ref), _width(r)
        if rw is not None and mw is not None:
            width_errs.append(mw - rw)

    def share(errs: list[int], pred) -> str:
        return f"{sum(1 for e in errs if pred(e))}/{len(errs)}" if errs else "–"

    def mae(errs: list[int]) -> str:
        return f"{statistics.mean(abs(e) for e in errs):.1f}" if errs else "–"

    def med(errs: list[int]) -> str:
        return f"{statistics.median(errs):+.0f}" if errs else "–"

    q = statistics.quantiles(widths, n=4) if len(widths) >= 4 else []
    return [
        f"| songs measured | {len(results)} |",
        f"| no range / labelled | {no_range} / {labelled} |",
        f"| width median (quartiles) | "
        + (f"{statistics.median(widths):.0f} ({q[0]:.0f}–{q[2]:.0f})" if q else "–")
        + " |",
        f"| width ≥ 30 | {sum(1 for w in widths if w >= 30)} |",
        f"| top ≥ C6 | {tops} |",
        f"| vs reference, low note (mod octave): mean abs / median | {mae(low_errs)} / {med(low_errs)} |",
        f"| vs reference, high note (mod octave): mean abs / median | {mae(high_errs)} / {med(high_errs)} |",
        f"| vs reference, width: mean abs / median | {mae(width_errs)} / {med(width_errs)} |",
        f"| within ±{CLOSE} (low, high, width) | {share(low_errs, lambda e: abs(e) <= CLOSE)}, "
        f"{share(high_errs, lambda e: abs(e) <= CLOSE)}, "
        f"{share(width_errs, lambda e: abs(e) <= CLOSE)} |",
        f"| width off by ≥{OCTAVE_ERROR} (an end an octave out) | "
        f"{share(width_errs, lambda e: abs(e) >= OCTAVE_ERROR)} |",
        f"| rapped / instrumental songs given no sung range | "
        + (f"{kinds_right}/{kinds_total}" if kinds_total else "–")
        + " |",
    ]


def per_song_table(
    songs: list[TestSong],
    all_results: dict[str, dict[str, RangeResult]],
    refs: dict[str, Reference],
) -> list[str]:
    names = list(all_results)
    head = "| song | picked | stored | reference | " + " | ".join(names) + " |"
    lines = [head, "|" + "---|" * (4 + len(names))]
    for song in songs:
        sid = song["song_id"]
        ref = refs.get(sid, {})
        kind = ref.get("kind", "sung")
        if kind != "sung":
            ref_cell = kind
        elif ref.get("low"):
            ref_cell = f"{ref.get('low')}–{ref.get('high')}"
        else:
            ref_cell = ""
        stored = (
            f"{song['stored_low']}–{song['stored_high']}" if song["stored_low"] else ""
        )
        cells = []
        for name in names:
            r = all_results[name].get(sid)
            if r is None:
                cells.append("(no contour)")
            elif r.label:
                cells.append(r.label)
            elif r.low is None:
                cells.append("none")
            else:
                cell = f"{r.low}–{r.high}"
                rw, mw = _ref_width(ref), _width(r)
                if rw is not None and mw is not None:
                    lo = _pc_err(r.low, ref.get("low"))
                    hi = _pc_err(r.high, ref.get("high"))
                    cell += f" ({lo:+d}/{hi:+d}, w{mw - rw:+d})"
                cells.append(cell)
        title = f"{song['artist']} – {song['title']}"[:60]
        lines.append(
            f"| {title} | {song['picked_as']} | {stored} | {ref_cell} | "
            + " | ".join(cells)
            + " |"
        )
    return lines


RAP_SWEEP = [round(0.03 + 0.01 * i, 2) for i in range(11)]
LABEL_METHOD = "notes+lead+labels"


def known_kinds(refs: dict[str, Reference], answers: dict) -> dict[str, str]:
    """Each song's kind: the ear answer where given, else the reference set's."""
    kinds = {sid: r["kind"] for sid, r in refs.items() if r.get("kind")}
    for sid, song_answers in answers.items():
        if song_answers.get("kind"):
            kinds[sid] = song_answers["kind"]
    return kinds


def rap_sweep(results: dict[str, RangeResult], kinds: dict[str, str]) -> list[str]:
    """For each pitched-share threshold: songs it would wrongly call rapped,
    rapped songs it would miss. Picks RAPPED_BELOW_SHARE from the ear answers."""
    shares = {
        sid: r.detail.get("pitched_share")
        for sid, r in results.items()
        if r.detail.get("pitched_share") is not None and sid in kinds
        # Labelled before the rap check runs: its share says nothing about rap.
        and r.label != "no lead found"
    }
    if not shares:
        return ["No songs with a known kind yet."]
    counts = {
        k: sum(1 for sid in shares if kinds[sid] == k)
        for k in ("sung", "mixed", "rapped", "spoken")
    }
    lines = [
        f"Songs with a known kind: {len(shares)} "
        + ", ".join(f"{k} {n}" for k, n in counts.items() if n),
        "",
        "| below | sung called rapped | rapped/spoken missed | mixed called rapped |",
        "|---|---|---|---|",
    ]
    for threshold in RAP_SWEEP:
        sung = sum(
            1 for sid, s in shares.items() if kinds[sid] == "sung" and s < threshold
        )
        missed = sum(
            1
            for sid, s in shares.items()
            if kinds[sid] in ("rapped", "spoken") and s >= threshold
        )
        mixed = sum(
            1 for sid, s in shares.items() if kinds[sid] == "mixed" and s < threshold
        )
        lines.append(f"| {threshold:.2f} | {sung} | {missed} | {mixed} |")
    return lines


def ear_verdicts() -> list[str]:
    """Each method's ends as judged on the admin Check vocal range page."""
    from app.services.vocal_range_review import MOMENT_ANSWERS, list_songs

    listing = list_songs()
    lines = [
        "An end's verdict is the answer to its first answered moment ('can't tell' skipped).",
        "",
        "| method | judged | " + " | ".join(MOMENT_ANSWERS[:-1]) + " |",
        "|---|---|" + "---|" * (len(MOMENT_ANSWERS) - 1),
    ]
    for method, verdicts in listing["verdicts"].items():
        judged = sum(verdicts.values())
        cells = [
            f"{verdicts.get(a, 0)}"
            + (f" ({verdicts.get(a, 0) / judged:.0%})" if judged else "")
            for a in MOMENT_ANSWERS[:-1]
        ]
        lines.append(f"| {method} | {judged} | " + " | ".join(cells) + " |")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("methods", nargs="*", default=list(METHODS))
    args = parser.parse_args()

    songs = load_testset()
    refs = load_reference()
    all_results = {name: run_method(name, songs) for name in args.methods}

    out = [
        "# Vocal range benchmark",
        "",
        f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · {len(songs)} songs · "
        f"{sum(1 for r in refs.values() if r.get('low'))} with a sheet-music range",
        "",
        "Per song: method minus reference in semitones, low/high modulo the octave, then width (w).",
        "",
    ]
    for name, results in all_results.items():
        out += [f"## {name}", "", "| | |", "|---|---|", *summary(results, refs), ""]
    out += ["## By ear", "", *ear_verdicts(), ""]
    answers_path = RESULTS_DIR / "answers.json"
    answers = json.loads(answers_path.read_text()) if answers_path.exists() else {}
    if LABEL_METHOD in all_results:
        out += [
            f"## Rap threshold ({LABEL_METHOD} pitched share)",
            "",
            *rap_sweep(all_results[LABEL_METHOD], known_kinds(refs, answers)),
            "",
        ]
    out += ["## Per song", "", *per_song_table(songs, all_results, refs), ""]
    REPORT_PATH.write_text("\n".join(out))
    print("\n".join(out[: 8 + 12 * len(all_results)]))
    print(f"... full report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
