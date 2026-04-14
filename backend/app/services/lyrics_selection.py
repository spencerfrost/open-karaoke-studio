from typing import Literal, Optional, TypedDict

from app.config.logging import get_structured_logger

logger = get_structured_logger(
    "app.services.lyrics_selection",
    {"component": "lyrics_selection"},
)


class AlignmentAttempt(TypedDict):
    content: str
    source_type: Literal["plain", "synced"]
    source: str
    persist: bool


def build_alignment_attempts(
    song,
    include_remote: bool = True,
    max_remote_results: int = 3,
) -> list[AlignmentAttempt]:
    """Build ordered lyric-alignment attempts for a song."""
    attempts: list[AlignmentAttempt] = []
    seen: set[tuple[str, str]] = set()

    def add_attempt(
        content: Optional[str],
        source_type: Literal["plain", "synced"],
        source: str,
        persist: bool = False,
    ) -> None:
        if not content:
            return
        text = content.strip()
        if not text:
            return
        key = (source_type, text)
        if key in seen:
            return
        seen.add(key)
        attempts.append(
            {
                "content": text,
                "source_type": source_type,
                "source": source,
                "persist": persist,
            }
        )

    add_attempt(song.plain_lyrics, "plain", "db:plain")
    add_attempt(song.synced_lyrics, "synced", "db:synced")

    if not include_remote:
        return attempts

    track_name = (song.title or "").strip()
    artist_name = (song.artist or "").strip()
    if not track_name or not artist_name:
        return attempts

    from app.services.lyrics_service import LyricsService
    from app.services.syncedlyrics_service import SyncedLyricsService

    params = {
        "track_name": track_name,
        "artist_name": artist_name,
    }
    if song.album:
        params["album_name"] = song.album

    try:
        lrclib_results = LyricsService().search_lyrics_structured(params)
        for idx, candidate in enumerate(lrclib_results[:max_remote_results]):
            add_attempt(
                candidate.get("plainLyrics"),
                "plain",
                f"lrclib:{idx + 1}",
                persist=True,
            )
            add_attempt(
                candidate.get("syncedLyrics"),
                "synced",
                f"lrclib:{idx + 1}",
                persist=True,
            )
    except Exception:
        logger.debug(
            "LRCLIB candidate fetch failed for %s - %s",
            artist_name,
            track_name,
            exc_info=True,
        )

    try:
        synced_results = SyncedLyricsService().search_lyrics_structured(params)
        for idx, candidate in enumerate(synced_results[:max_remote_results]):
            add_attempt(
                candidate.get("plainLyrics"),
                "plain",
                f"syncedlyrics:{idx + 1}",
                persist=True,
            )
            add_attempt(
                candidate.get("syncedLyrics"),
                "synced",
                f"syncedlyrics:{idx + 1}",
                persist=True,
            )
    except Exception:
        logger.debug(
            "syncedlyrics candidate fetch failed for %s - %s",
            artist_name,
            track_name,
            exc_info=True,
        )

    return attempts