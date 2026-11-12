"""
Score every run in results/runs/ and write results/report.md + per_song.csv.

    python scripts/experiments/song_versions/score.py

No truth needed (every song):
  covered_album  share of lead singing (singing map) with an album line on screen
  covered    the same, counting transcript lines too
  ghost      share of on-screen line time with no lead or backing singing
  heard      share of on-screen line time from heard (transcript) lines
  album      share of the album's lines shown at least once
  repeats    album lines shown again after their first time
  tail       seconds of lead singing more than 2 s after the last line
Controls (already right today): how far each album line's start moved from
today's, matched by album line, first time each line is shown.
Synthetic (truth known): album lines found within 0.5 s of where they're
sung, and whether lines the album lacks get anything on screen.
Detection: candidate "this is another version" rules on today's timing, by kind.

A line is on screen from its first word's start to its last word's end.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from statistics import mean, median
from typing import Any, Optional

from common import (
    REPORT_PATH,
    RESULTS_DIR,
    RUNS_DIR,
    Interval,
    TestSong,
    album_lines,
    intersect,
    line_spans,
    load_testset,
    subtract,
    sung,
    tokens,
    total,
    union,
)

from app.services.lyrics_retiming import _longest_common_subsequence  # noqa: E402

TAIL_MARGIN = 2.0
CONTROL_MOVED = 0.5
TRUTH_WITHIN = 0.5
# A transcribed line counts as on time when a line starts within this of it.
TRUTH_ON_TIME = 1.0


def _screen(spans: dict[int, Interval]) -> list[Interval]:
    return union(sorted(spans.values()))


def _first_starts(result: dict[str, Any]) -> dict[int, float]:
    """Each album line's start, the first time it's shown."""
    spans = line_spans(result["words"])
    starts: dict[int, float] = {}
    for index, (start, _) in sorted(spans.items(), key=lambda item: item[1][0]):
        album_index = result["lines"][index]["album_index"]
        if album_index is not None and album_index not in starts:
            starts[album_index] = start
    return starts


def score_song(
    song: TestSong, result: dict[str, Any], today: Optional[dict[str, Any]]
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "song_id": song["song_id"],
        "kind": song["kind"],
        "picked_as": song["picked_as"],
        "song": f"{song['artist']} - {song['title']}",
    }
    if "error" in result:
        row["error"] = result["error"]
        return row
    spans = line_spans(result["words"])
    screen = _screen(spans)
    lead = [(a, b) for a, b in song["lead"] or []]
    shown = total(screen)
    heard_time = sum(
        b - a for i, (a, b) in spans.items() if result["lines"][i]["source"] == "heard"
    )
    seen: set[int] = set()
    repeats = 0
    for index, _ in sorted(spans.items(), key=lambda item: item[1][0]):
        album_index = result["lines"][index]["album_index"]
        if album_index is None:
            continue
        repeats += album_index in seen
        seen.add(album_index)
    last_end = max((b for _, b in spans.values()), default=0.0)
    album_screen = _screen(
        {i: s for i, s in spans.items() if result["lines"][i]["source"] == "album"}
    )
    row.update(
        {
            "lines": len(spans),
            "album_lines_shown": len(seen),
            "mean_score": result.get("mean_score"),
            "covered": (
                round(total(intersect(lead, screen)) / total(lead), 3) if lead else None
            ),
            "covered_album": (
                round(total(intersect(lead, album_screen)) / total(lead), 3)
                if lead
                else None
            ),
            "ghost": (
                round(total(subtract(screen, sung(song))) / shown, 3)
                if shown and (song["lead"] is not None)
                else None
            ),
            "heard": round(heard_time / shown, 3) if shown else 0.0,
            "album": round(
                len(seen)
                / max(
                    1,
                    len(
                        album_lines(
                            song.get("version_lrc", "")
                            if result.get("lyrics") == "version"
                            else song["album_lrc"]
                        )
                    ),
                ),
                3,
            ),
            "repeats": repeats,
            "tail": round(total(intersect(lead, [(last_end + TAIL_MARGIN, 1e9)])), 1),
        }
    )

    if song["kind"] == "control" and today and "error" not in today:
        mine, theirs = _first_starts(result), _first_starts(today)
        moves = [abs(mine[i] - theirs[i]) for i in theirs if i in mine]
        if moves:
            moves.sort()
            row["control_median_move"] = round(median(moves), 2)
            row["control_p90_move"] = round(moves[int(0.9 * (len(moves) - 1))], 2)
            row["control_moved_share"] = round(
                sum(m > CONTROL_MOVED for m in moves) / len(moves), 3
            )
        row["control_missing"] = sum(i not in mine for i in theirs)

    if song["truth"]:
        by_album: dict[int, list[float]] = defaultdict(list)
        for index, (start, _) in spans.items():
            album_index = result["lines"][index]["album_index"]
            if album_index is not None:
                by_album[album_index].append(start)
        truth_album = [
            (t["album_index"], t["start"])
            for t in song["truth"]
            if t["album_index"] is not None
        ]
        found = sum(
            any(abs(s - start) <= TRUTH_WITHIN for s in by_album[album_index])
            for album_index, start in truth_album
        )
        row["truth_found"] = round(found / len(truth_album), 3) if truth_album else None
        span_end = song.get("truth_span", [0.0, 1e9])[1]
        starts = [t["start"] for t in song["truth"]] + [span_end]
        new_lines = [
            (t, (t["start"], starts[k + 1]))
            for k, t in enumerate(song["truth"])
            if t["album_index"] is None
        ]
        if new_lines:
            line_starts = [start for start, _ in spans.values()]
            row["truth_new_shown"] = round(
                sum(bool(intersect([window], screen)) for _, window in new_lines)
                / len(new_lines),
                3,
            )
            row["truth_new_on_time"] = round(
                sum(
                    any(abs(s - t["start"]) <= TRUTH_ON_TIME for s in line_starts)
                    for t, _ in new_lines
                )
                / len(new_lines),
                3,
            )
            # Words on screen while each line is sung, against its real words.
            heard_right = expected = 0
            for t, (a, b) in new_lines:
                truth_tokens = tokens(t["text"])
                shown_tokens = [
                    token
                    for w in sorted(result["words"], key=lambda w: w["start"])
                    if a - TRUTH_ON_TIME <= w["start"] < b
                    for token in tokens(w["word"])
                ]
                heard_right += len(
                    _longest_common_subsequence(truth_tokens, shown_tokens)
                )
                expected += len(truth_tokens)
            row["truth_new_words"] = round(heard_right / max(1, expected), 3)
    return row


def _load_runs() -> dict[str, dict[str, dict[str, Any]]]:
    runs: dict[str, dict[str, dict[str, Any]]] = {}
    if not RUNS_DIR.is_dir():
        return runs
    for folder in sorted(p for p in RUNS_DIR.iterdir() if p.is_dir()):
        runs[folder.name] = {
            path.stem: json.loads(path.read_text()) for path in folder.glob("*.json")
        }
    return runs


def _avg(rows: list[dict[str, Any]], key: str) -> str:
    values = [r[key] for r in rows if r.get(key) is not None]
    return f"{mean(values):.3g}" if values else "–"


def _detection(songs: list[TestSong]) -> list[str]:
    def last_word(song: TestSong) -> Optional[float]:
        words = (song["today"] or {}).get("words") or []
        return max((w["end"] for w in words), default=None)

    rules = {
        "untimed singing ≥ 15 s": lambda s: (s["untimed_before"] or 0)
        + (s["untimed_after"] or 0)
        >= 15,
        "untimed singing ≥ 30 s": lambda s: (s["untimed_before"] or 0)
        + (s["untimed_after"] or 0)
        >= 30,
        "song ≥ 45 s longer than last word": lambda s: bool(
            s["duration"] and last_word(s) and s["duration"] - last_word(s) >= 45
        ),
        "score < 0.4": lambda s: (s["today"] or {}).get("mean_score") is not None
        and s["today"]["mean_score"] < 0.4,  # type: ignore[index]
    }
    kinds = sorted({s["kind"] for s in songs if s["today"]})
    lines = [
        "| Rule | " + " | ".join(f"{k} flagged" for k in kinds) + " |",
        "|---|" + "---|" * len(kinds),
    ]
    for name, rule in rules.items():
        cells = []
        for kind in kinds:
            pool = [s for s in songs if s["kind"] == kind and s["today"]]
            cells.append(f"{sum(bool(rule(s)) for s in pool)}/{len(pool)}")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append(
        "Real versions include songs whose lyrics just miss a part; synthetic songs "
        "have no stored timing, so they're scored after `today` runs on them."
    )
    return lines


def main() -> None:
    songs = load_testset()
    by_id = {s["song_id"]: s for s in songs}
    runs = _load_runs()
    today = runs.get("today", {})

    rows: list[dict[str, Any]] = []
    for run_name, results in runs.items():
        for song_id, result in results.items():
            if song_id not in by_id:
                continue
            row = score_song(by_id[song_id], result, today.get(song_id))
            row["run"] = run_name
            rows.append(row)

    report = [
        "# Song versions benchmark",
        "",
        f"{len(songs)} test songs: "
        + ", ".join(
            f"{sum(s['kind'] == k for s in songs)} {k}"
            for k in ("real", "control", "synthetic")
        )
        + ".",
        "",
        "## By run and kind",
        "",
        "Read the album columns first. Transcript lines raise Singing covered and the "
        "score (Whisper's own words aligned back onto the audio it heard them in) "
        "without putting the song's lyrics on screen.",
        "",
        "- **Album lines shown**: share of the album's lines on screen at least once",
        "- **Singing covered by album lines**: share of lead singing under an album line",
        "- **Singing covered**: the same, counting transcript lines too",
        "- **Transcript share**: share of on-screen line time that is transcript text",
        "- **Lines on silence**: share of on-screen line time with no lead or backing",
        "- **Tail**: seconds of lead singing more than 2 s after the last line",
        "",
        "| Run | Kind | Songs | Errors | Album lines shown | Singing covered by album "
        "lines | Singing covered | Transcript share | Lines on silence | Repeats | "
        "Tail (s) | Score | Control moved > 0.5 s | Truth found | Transcribed lines: shown "
        "| on time | words right |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for run_name in runs:
        for kind in ("real", "control", "synthetic"):
            group = [r for r in rows if r["run"] == run_name and r["kind"] == kind]
            if not group:
                continue
            ok = [r for r in group if "error" not in r]
            report.append(
                f"| {run_name} | {kind} | {len(group)} | {len(group) - len(ok)} | "
                f"{_avg(ok, 'album')} | {_avg(ok, 'covered_album')} | "
                f"{_avg(ok, 'covered')} | {_avg(ok, 'heard')} | {_avg(ok, 'ghost')} | "
                f"{_avg(ok, 'repeats')} | {_avg(ok, 'tail')} | "
                f"{_avg(ok, 'mean_score')} | {_avg(ok, 'control_moved_share')} | "
                f"{_avg(ok, 'truth_found')} | {_avg(ok, 'truth_new_shown')} | "
                f"{_avg(ok, 'truth_new_on_time')} | {_avg(ok, 'truth_new_words')} |"
            )
    report += ["", "## Detection rules (today's timing)", "", *_detection(songs), ""]

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(report))
    columns = sorted({key for row in rows for key in row})
    front = ["run", "kind", "picked_as", "song", "song_id"]
    columns = front + [c for c in columns if c not in front]
    with open(RESULTS_DIR / "per_song.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["run"], r["kind"], r["song"])))
    print(f"Wrote {REPORT_PATH} ({len(rows)} scored results)")


if __name__ == "__main__":
    main()
