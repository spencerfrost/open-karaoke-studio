"""Helpers for lyrics alignment task execution."""

from collections.abc import Collection
from pathlib import Path

from app.services.lyrics_selection import SongData, build_alignment_attempts


def run_alignment_attempt(*, attempt: dict, vocals_path: Path, language: str):
    """Run strict WhisperX forced alignment for one synced lyrics candidate.

    Plain lyrics have no timestamps to anchor WhisperX, so they are never
    aligned; the task sends plain-only songs to ASR instead.
    """
    from app.services.lyrics_alignment import align_lyrics_to_vocals

    return align_lyrics_to_vocals(attempt["content"], vocals_path, language=language)


def build_alignment_attempts_for_song(
    song: SongData,
    include_remote: bool = True,
    max_remote_results: int = 3,
    rejected_keys: Collection[str] = (),
) -> list[dict]:
    """Build ordered lyrics-source attempts for alignment."""
    return build_alignment_attempts(
        song,
        include_remote=include_remote,
        max_remote_results=max_remote_results,
        rejected_keys=rejected_keys,
    )
