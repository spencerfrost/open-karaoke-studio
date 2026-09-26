"""Helpers for lyrics alignment task execution."""

from pathlib import Path

from app.services.lyrics_selection import SongData, build_alignment_attempts

from ._shared import _make_alignment_cache_key


def run_alignment_attempt(
    *,
    attempt: dict,
    vocals_path: Path,
    language: str,
    alignment_cache: dict[tuple[str, str, str, str], dict | None],
    alignment_mode: str,
):
    """Run one alignment attempt and memoize by source/language/mode."""
    from app.services.lyrics_alignment import align_plain_lyrics_to_vocals, align_synced_lyrics_to_vocals

    cache_key = _make_alignment_cache_key(
        source_type=attempt["source_type"],
        content=attempt["content"],
        language=language,
        alignment_mode=alignment_mode,
    )
    if cache_key in alignment_cache:
        return alignment_cache[cache_key]

    if attempt["source_type"] == "plain":
        result = align_plain_lyrics_to_vocals(
            attempt["content"],
            vocals_path,
            language=language,
            alignment_mode=alignment_mode,
        )
    else:
        result = align_synced_lyrics_to_vocals(
            attempt["content"],
            vocals_path,
            language=language,
            mode=alignment_mode,
        )

    alignment_cache[cache_key] = result
    return result


def build_alignment_attempts_for_song(
    song: SongData,
    include_remote: bool = True,
    max_remote_results: int = 3,
) -> list[dict]:
    """Build ordered lyrics-source attempts for alignment."""
    return build_alignment_attempts(
        song,
        include_remote=include_remote,
        max_remote_results=max_remote_results,
    )
