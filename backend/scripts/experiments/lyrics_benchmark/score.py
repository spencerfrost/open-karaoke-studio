#!/usr/bin/env python3
"""Score every cached run against the test set; write results/report.md and per-song CSVs.

ASR is scored by word error rate against the LRC text. "Lead WER" drops
"(...)" spans from the reference, since vocals.mp3 is the lead stem and
parentheses mostly hold backing vocals; "full WER" keeps them. A failed song
counts as an empty transcript (every word missed).

Alignment is scored by each line's start (its first timed word) against the
LRC line time. Shares within 0.3/0.5/1.0 s count every line, so a line the
model couldn't place counts as a miss; median/p90 error cover placed lines.

Run from backend/ with the venv active:
    python scripts/experiments/lyrics_benchmark/score.py
"""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from common import (
    BLOCKS_VERSION,
    RESULTS_DIR,
    RUNS_DIR,
    EditCounts,
    TestSong,
    edit_counts,
    load_testset,
    normalize_words,
    read_run,
    reference_lines,
)
from run_models import MODELS

THRESHOLDS = (0.3, 0.5, 1.0)
SONG_PASS_SECONDS = 1.0
SONG_PASS_SHARE = 0.9


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *("| " + " | ".join(row) + " |" for row in rows),
    ]


def models_with_runs(task: str) -> list[str]:
    return [
        name
        for name, spec in MODELS.items()
        if spec.task == task and (RUNS_DIR / name).is_dir()
    ]


# ---------------------------------------------------------------------------
# ASR
# ---------------------------------------------------------------------------


def score_asr(songs: list[TestSong]) -> tuple[list[str], list[dict]]:
    models = models_with_runs("asr")
    if not models:
        return [], []

    per_song: list[dict] = []
    rows: list[list[str]] = []
    by_language: dict[str, dict[str, EditCounts]] = defaultdict(dict)
    for model in models:
        lead_total, full_total = EditCounts(), EditCounts()
        song_wers: list[float] = []
        seconds: list[float] = []
        ran = failed = 0
        for song in songs:
            run = read_run(model, song["song_id"])
            if run is None:
                continue
            ran += 1
            failed += "error" in run
            seconds.append(run["elapsed_s"])
            reference = " ".join(
                line["text"] for line in reference_lines(song["synced_lyrics"])
            )
            hypothesis = run.get("text") or ""
            lead = edit_counts(
                normalize_words(reference, drop_parenthetical=True),
                normalize_words(hypothesis, drop_parenthetical=True),
            )
            full = edit_counts(
                normalize_words(reference, drop_parenthetical=False),
                normalize_words(hypothesis, drop_parenthetical=False),
            )
            lead_total += lead
            full_total += full
            song_wers.append(lead.wer)
            language = song["language"]
            by_language[language][model] = (
                by_language[language].get(model, EditCounts()) + lead
            )
            per_song.append(
                {
                    "model": model,
                    "song_id": song["song_id"],
                    "artist": song["artist"],
                    "title": song["title"],
                    "language": language,
                    "lead_wer": round(lead.wer, 4),
                    "full_wer": round(full.wer, 4),
                    "substitutions": lead.substitutions,
                    "deletions": lead.deletions,
                    "insertions": lead.insertions,
                    "reference_words": lead.reference_words,
                    "error": run.get("error", ""),
                    "elapsed_s": run["elapsed_s"],
                }
            )
        if not ran:
            continue
        words = lead_total.reference_words or 1
        rows.append(
            [
                model,
                f"{ran}/{len(songs)}",
                str(failed),
                f"**{percent(lead_total.wer)}**",
                percent(full_total.wer),
                percent(statistics.median(song_wers)),
                percent(lead_total.substitutions / words),
                percent(lead_total.deletions / words),
                percent(lead_total.insertions / words),
                f"{statistics.mean(seconds):.1f}",
            ]
        )

    lines = [
        "## Transcription (ASR)",
        "",
        "Lower is better. Lead WER ignores `(...)` backing lines; Sub/Del/Ins split",
        "the lead errors (Del = words not heard, Ins = words made up).",
        "",
        *table(
            [
                "Model",
                "Songs",
                "Failed",
                "Lead WER",
                "Full WER",
                "Median song WER",
                "Sub",
                "Del",
                "Ins",
                "Sec/song",
            ],
            rows,
        ),
    ]
    if len(by_language) > 1:
        language_counts = defaultdict(int)
        for song in songs:
            language_counts[song["language"]] += 1
        language_rows = [
            [f"{language} ({language_counts[language]})"]
            + [
                (
                    percent(by_language[language][m].wer)
                    if m in by_language[language]
                    else "–"
                )
                for m in models
            ]
            for language in sorted(by_language, key=lambda l: -language_counts[l])
        ]
        lines += [
            "",
            "Lead WER by language:",
            "",
            *table(["Language", *models], language_rows),
        ]
    return lines, per_song


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------


def _within(errors: list[float], threshold: float, total: int) -> float:
    return sum(abs(e) <= threshold for e in errors) / total if total else 0.0


def _p90(errors: list[float]) -> float:
    absolute = sorted(abs(e) for e in errors)
    return absolute[int(0.9 * (len(absolute) - 1))]


def score_align(songs: list[TestSong]) -> tuple[list[str], list[dict]]:
    """Raw and offset-corrected line-start errors.

    Many LRCs are shifted by a constant second or more (the problem
    lyrics_offset.sweep_lrc_offset fixes in the app). Raw error charges that
    shift to the model. Offset-corrected error removes each model's own
    median shift per song first, so it measures how well the model places
    lines relative to each other, which is what an aligner controls.
    """
    models = models_with_runs("align")
    if not models:
        return [], []

    per_song: list[dict] = []
    stale: set[str] = set()
    song_shifts: dict[str, dict[str, float]] = defaultdict(dict)
    rows: list[list[str]] = []
    for model in models:
        all_lines = 0
        raw: list[float] = []  # signed, placed lines only
        corrected: list[float] = []
        passing_songs = 0
        seconds: list[float] = []
        ran = failed = 0
        for song in songs:
            run = read_run(model, song["song_id"])
            if run is None:
                continue
            if run.get("blocks_version") != BLOCKS_VERSION and "error" not in run:
                stale.add(model)
                continue
            ran += 1
            failed += "error" in run
            seconds.append(run["elapsed_s"])
            reference = reference_lines(song["synced_lyrics"])
            predicted = run.get("line_starts") or [None] * len(reference)
            song_raw = [
                p - r["start"] for p, r in zip(predicted, reference) if p is not None
            ]
            shift = statistics.median(song_raw) if song_raw else 0.0
            song_corrected = [e - shift for e in song_raw]
            if song_raw:
                song_shifts[song["song_id"]][model] = shift
            all_lines += len(reference)
            raw += song_raw
            corrected += song_corrected
            song_within = sum(abs(e) <= SONG_PASS_SECONDS for e in song_corrected)
            passing_songs += song_within >= SONG_PASS_SHARE * len(reference)
            per_song.append(
                {
                    "model": model,
                    "song_id": song["song_id"],
                    "artist": song["artist"],
                    "title": song["title"],
                    "language": song["language"],
                    "lines": len(reference),
                    "placed": len(song_raw),
                    "shift_s": round(shift, 3),
                    "raw_within_0.5s": round(_within(song_raw, 0.5, len(reference)), 3),
                    "corrected_within_0.5s": round(
                        _within(song_corrected, 0.5, len(reference)), 3
                    ),
                    "corrected_median_abs_s": (
                        round(statistics.median(abs(e) for e in song_corrected), 3)
                        if song_corrected
                        else ""
                    ),
                    "error": run.get("error", "")
                    or "; ".join(run.get("block_errors", [])),
                    "elapsed_s": run["elapsed_s"],
                }
            )
        if not ran:
            continue
        rows.append(
            [
                model,
                f"{ran}/{len(songs)}",
                str(failed),
                percent(1 - len(raw) / all_lines) if all_lines else "–",
                percent(_within(raw, 0.5, all_lines)),
                percent(_within(raw, 1.0, all_lines)),
                *(
                    (
                        f"**{percent(_within(corrected, t, all_lines))}**"
                        if t == 0.5
                        else percent(_within(corrected, t, all_lines))
                    )
                    for t in THRESHOLDS
                ),
                (
                    f"{statistics.median(abs(e) for e in corrected):.2f}"
                    if corrected
                    else "–"
                ),
                f"{_p90(corrected):.2f}" if corrected else "–",
                percent(passing_songs / ran),
                f"{statistics.mean(seconds):.1f}",
            ]
        )

    lines = [
        "## Alignment",
        "",
        'Line start vs the LRC time. Higher "within" is better; unplaced lines count as misses.',
        "Raw = straight against the LRC. Corrected = after removing the model's median",
        "shift for that song, which takes out LRC files that are off by a constant amount.",
        f"Songs OK = songs with at least {percent(SONG_PASS_SHARE)} of lines within"
        f" {SONG_PASS_SECONDS:.0f} s (corrected).",
        "",
        *table(
            [
                "Model",
                "Songs",
                "Failed",
                "Unplaced",
                "Raw ≤0.5s",
                "Raw ≤1s",
                *(f"Corrected ≤{t}s" for t in THRESHOLDS),
                "Corrected median (s)",
                "Corrected P90 (s)",
                "Songs OK",
                "Sec/song",
            ],
            rows,
        ),
    ]

    if stale:
        lines += [
            "",
            f"Skipped results from older block definitions for: {', '.join(sorted(stale))}."
            f" Rerun with --force.",
        ]

    # Songs where two independent aligners agree on a shift: the LRC is off.
    if {"wav2vec2", "mms-fa"} <= set(models):
        shifted = [
            (song_id, (s["wav2vec2"] + s["mms-fa"]) / 2)
            for song_id, s in song_shifts.items()
            if {"wav2vec2", "mms-fa"} <= set(s)
            and abs(s["wav2vec2"] - s["mms-fa"]) <= 0.25
            and abs(s["wav2vec2"] + s["mms-fa"]) / 2 > 0.5
        ]
        lines += [
            "",
            f"Test-set note: in {len(shifted)} of {len(songs)} songs, wav2vec2 and mms-fa agree"
            " (within 0.25 s) that the LRC is shifted by more than 0.5 s"
            + (
                f" (largest {max(abs(x) for _, x in shifted):.1f} s)."
                if shifted
                else "."
            ),
        ]
    return lines, per_song


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    songs = load_testset()
    languages: dict[str, int] = defaultdict(int)
    for song in songs:
        languages[song["language"]] += 1

    asr_lines, asr_rows = score_asr(songs)
    align_lines, align_rows = score_align(songs)
    timing_note = [
        "",
        "Sec/song for production models (whisper-*, qwen3-asr-*, wav2vec2) includes",
        "loading the model for every song, as the app does; mms-fa and qwen3-fa load once.",
    ]
    report = [
        "# Lyrics model benchmark",
        "",
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · {len(songs)} songs, one per artist · "
        + ", ".join(
            f"{lang} {n}" for lang, n in sorted(languages.items(), key=lambda x: -x[1])
        ),
        "",
        *asr_lines,
        "",
        *align_lines,
        *timing_note,
        "",
    ]
    report_path = RESULTS_DIR / "report.md"
    report_path.write_text("\n".join(report))
    write_csv(RESULTS_DIR / "per_song_asr.csv", asr_rows)
    write_csv(RESULTS_DIR / "per_song_align.csv", align_rows)
    print("\n".join(report))
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
