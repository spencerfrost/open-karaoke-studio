"""
Transcribe each test song's vocals once per ASR model and cache the result.

Every ASR method reads the cache, so trying a new method costs only its forced
alignment. Runs the app's own transcription (`transcribe_lyrics_from_vocals`),
in the test set's language, never a detected one. Uses the GPU; resumable.

    python scripts/experiments/song_versions/transcribe.py                 # whisper-small
    python scripts/experiments/song_versions/transcribe.py --asr whisper-large-v3-turbo
    python scripts/experiments/song_versions/transcribe.py --song <song_id>

Writes results/transcripts/<asr>/<song_id>.json:
    {"asr", "model", "language", "segments": [{"start", "end", "text"}],
     "words": [{"word", "start", "end", "score", "line_index"}]}
A word's line_index is its Whisper segment.
"""

from __future__ import annotations

import argparse
import json
import logging
from time import perf_counter

from common import (
    ASR_MODELS,
    DEFAULT_ASR,
    load_testset,
    transcript_path,
    vocals_path,
)

from app.services.lyrics_transcription import (  # noqa: E402
    transcribe_lyrics_from_vocals,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[1])
    parser.add_argument("--asr", choices=sorted(ASR_MODELS), default=DEFAULT_ASR)
    parser.add_argument("--song", nargs="*", default=[], help="only these song ids")
    parser.add_argument("--kind", choices=["real", "control", "synthetic"])
    parser.add_argument("--force", action="store_true", help="redo cached songs")
    parser.add_argument(
        "--batch-size", type=int, default=16, help="lower it when the GPU is shared"
    )
    parser.add_argument(
        "--device", default="auto", help="auto, cuda or cpu (cpu when the GPU is busy)"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(message)s")

    songs = load_testset()
    if args.song:
        songs = [s for s in songs if s["song_id"] in args.song]
    if args.kind:
        songs = [s for s in songs if s["kind"] == args.kind]

    for position, song in enumerate(songs, 1):
        path = transcript_path(args.asr, song["song_id"])
        label = f"[{position}/{len(songs)}] {song['artist']} - {song['title']}"
        if path.exists() and not args.force:
            continue
        started = perf_counter()
        try:
            result = transcribe_lyrics_from_vocals(
                vocals_path(song),
                language=song["language"],
                model_name=ASR_MODELS[args.asr],
                provider="whisperx",
                device=args.device,
                batch_size=args.batch_size,
            )
        except Exception as exc:  # a GPU shared with Celery can run out mid-run
            print(f"{label}: failed ({exc!r}); rerun to retry")
            continue
        if result is None:
            print(f"{label}: no transcript")
            continue
        words = result["alignment"]["words"]
        segments = []
        for index, line in enumerate(result["plain_lyrics"].splitlines()):
            line_words = [w for w in words if w["line_index"] == index]
            if not line_words:
                continue
            segments.append(
                {
                    "start": line_words[0]["start"],
                    "end": line_words[-1]["end"],
                    "text": line,
                }
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "asr": args.asr,
                    "model": result["asr_model"],
                    "language": song["language"],
                    "segments": segments,
                    "words": words,
                },
                ensure_ascii=False,
            )
        )
        print(
            f"{label}: {len(words)} words, {len(segments)} segments, "
            f"{perf_counter() - started:.0f}s"
        )


if __name__ == "__main__":
    main()
