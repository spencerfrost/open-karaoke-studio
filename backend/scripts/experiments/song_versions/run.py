"""
Run methods over the test set: plan, then force-align, the same way for all.

    python scripts/experiments/song_versions/run.py --list
    python scripts/experiments/song_versions/run.py today line-match+fill
    python scripts/experiments/song_versions/run.py line-match --asr whisper-large-v3-turbo
    python scripts/experiments/song_versions/run.py line-match --song <song_id> --force

ASR methods read results/transcripts/<asr>/ (transcribe.py first). Alignment
uses the GPU and the app's aligners on the lead + backing mix, as production
does. Resumable: songs already in results/runs/<method>[@<asr>]/ are skipped.

Each result: {"song_id", "method", "asr", "lines": [{"text", "source",
"album_index"}], "words": [...line_index into lines], "mean_score", "notes",
"chunks"} or {"song_id", "error"}.
"""

from __future__ import annotations

import argparse
import json
import logging
import traceback
from time import perf_counter
from typing import Any, Mapping, Optional, Sequence

from common import (
    ASR_MODELS,
    DEFAULT_ASR,
    Plan,
    PlanChunk,
    PlanLine,
    TestSong,
    album_lines,
    load_testset,
    load_transcript,
    run_dir,
    sung,
    vocals_path,
)
from methods import METHODS, Context

from app.services.lyrics_alignment import (  # noqa: E402
    LineChunk,
    align_line_chunks,
    align_lyrics_to_vocals,
)


def _from_lrc_words(
    lrc: str, words: Sequence[Mapping[str, Any]]
) -> tuple[list[PlanLine], list[dict[str, Any]]]:
    """Words stored against an LRC (line_index = LRC line, blanks counted),
    re-indexed onto its sung lines."""
    lines = album_lines(lrc)
    by_lrc_index = {line["lrc_index"]: line["index"] for line in lines}
    out = [
        {**word, "line_index": by_lrc_index[word["line_index"]]}
        for word in words
        if word["line_index"] in by_lrc_index
    ]
    plan_lines = [
        PlanLine(text=line["text"], source="album", album_index=line["index"])
        for line in lines
    ]
    return plan_lines, out


# auto, cuda or cpu: set from --device.
DEVICE = "auto"


def align(song: TestSong, plan: Plan) -> dict[str, Any]:
    language = song["language"]
    if "stored" in plan:
        lines, words = _from_lrc_words(plan["stored"]["lrc"], plan["stored"]["words"])
        return {
            "lines": lines,
            "words": words,
            "mean_score": plan["stored"]["mean_score"],
        }

    if "lrc" in plan:
        result = align_lyrics_to_vocals(
            plan["lrc"], vocals_path(song), language=language, device=DEVICE
        )
        if result is None:
            return {"error": "alignment returned nothing"}
        lines, words = _from_lrc_words(plan["lrc"], result["words"])
        # The album index survives a shift: keep the plan's.
        out = {
            "lines": list(plan.get("lrc_lines", lines)),
            "words": words,
            "mean_score": result["mean_score"],
        }
        if not plan.get("chunks"):
            return out
        # Extra lines outside the LRC, aligned in their own stretches.
        extra = _align_chunks(song, plan.get("chunks", []))
        if "error" in extra:
            return out
        offset = len(out["lines"])
        count = len(out["words"]) + len(extra["words"])
        return {
            "lines": out["lines"] + extra["lines"],
            "words": out["words"]
            + [{**w, "line_index": w["line_index"] + offset} for w in extra["words"]],
            "mean_score": round(
                (
                    out["mean_score"] * len(out["words"])
                    + extra["mean_score"] * len(extra["words"])
                )
                / max(1, count),
                3,
            ),
        }

    return _align_chunks(song, plan.get("chunks", []))


def _align_chunks(song: TestSong, plan_chunks: list[PlanChunk]) -> dict[str, Any]:
    flat: list[PlanLine] = []
    chunks: list[LineChunk] = []
    for chunk in plan_chunks:
        chunks.append(
            LineChunk(
                first_line=len(flat),
                last_line=len(flat) + len(chunk["lines"]) - 1,
                start=chunk["start"],
                end=chunk["end"],
            )
        )
        flat.extend(chunk["lines"])
    result = align_line_chunks(
        [line["text"] for line in flat],
        chunks,
        vocals_path(song),
        language=song["language"],
        device=DEVICE,
    )
    if result is None:
        return {"error": "alignment returned nothing"}
    return {"lines": flat, "words": result["words"], "mean_score": result["mean_score"]}


def run_one(song: TestSong, method_name: str, asr: Optional[str]) -> dict[str, Any]:
    method = METHODS[method_name]
    transcript = load_transcript(asr, song["song_id"]) if asr else None
    if method.uses_asr and transcript is None:
        return {"error": f"no {asr} transcript (run transcribe.py)"}
    ctx = Context(
        song=song,
        album=album_lines(song["album_lrc"]),
        transcript=transcript,
        sung=sung(song),
    )
    plan = method.plan(ctx)
    if plan is None:
        return {"error": "no plan", "plan_failed": True}
    result = align(song, plan)
    result["notes"] = plan.get("notes", {})
    if "chunks" in plan:
        result["chunks"] = [
            {"start": c["start"], "end": c["end"], "lines": len(c["lines"])}
            for c in plan["chunks"]
        ]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[1])
    parser.add_argument("methods", nargs="*")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--asr", choices=sorted(ASR_MODELS), default=DEFAULT_ASR)
    parser.add_argument("--song", nargs="*", default=[])
    parser.add_argument("--kind", choices=["real", "control", "synthetic"])
    parser.add_argument(
        "--lyrics",
        choices=["album", "version"],
        default="album",
        help="version: start from the version's own lyrics (add_version_lyrics.py); "
        "only songs that have them",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--device", default="auto", help="auto, cuda or cpu (cpu when the GPU is busy)"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    global DEVICE
    DEVICE = args.device

    if args.list or not args.methods:
        for method in METHODS.values():
            flags = ("asr" if method.uses_asr else "no asr") + (
                "" if method.ready else ", not built"
            )
            print(f"{method.name:18} ({flags}) {method.description}")
        return

    for name in args.methods:
        if name not in METHODS:
            raise SystemExit(f"Unknown method {name!r}; --list shows them")
        if not METHODS[name].ready:
            raise SystemExit(f"{name} is not built yet")

    songs = load_testset()
    if args.song:
        songs = [s for s in songs if s["song_id"] in args.song]
    if args.kind:
        songs = [s for s in songs if s["kind"] == args.kind]
    if args.lyrics == "version":
        songs = [
            {**s, "album_lrc": s["version_lrc"]}  # type: ignore[typeddict-item]
            for s in songs
            if s.get("version_lrc")
        ]

    for name in args.methods:
        asr = args.asr if METHODS[name].uses_asr else None
        out_dir = run_dir(name, asr, args.lyrics)
        out_dir.mkdir(parents=True, exist_ok=True)
        for position, song in enumerate(songs, 1):
            path = out_dir / f"{song['song_id']}.json"
            if path.exists() and not args.force:
                continue
            started = perf_counter()
            try:
                result = run_one(song, name, asr)
            except Exception as exc:  # one song's failure shouldn't stop the run
                result = {"error": repr(exc), "traceback": traceback.format_exc()}
            result = {
                "song_id": song["song_id"],
                "method": name,
                "asr": asr,
                "lyrics": args.lyrics,
                **result,
            }
            path.write_text(json.dumps(result, ensure_ascii=False))
            status = result.get("error") or (
                f"{len(result['lines'])} lines, score {result['mean_score']}"
            )
            print(
                f"{name}{'@' + asr if asr else ''} [{position}/{len(songs)}] "
                f"{song['artist']} - {song['title']}: {status} "
                f"({perf_counter() - started:.0f}s)"
            )


if __name__ == "__main__":
    main()
