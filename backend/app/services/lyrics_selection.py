from time import perf_counter
from typing import Literal, Optional, TypedDict

from app.config.logging import get_structured_logger
from app.services.lyrics_timing import log_lyrics_event

logger = get_structured_logger(
    "app.services.lyrics_selection",
    {"component": "lyrics_selection"},
)


class SongData(TypedDict):
    id: str
    title: Optional[str]
    artist: Optional[str]
    album: Optional[str]
    plain_lyrics: Optional[str]
    synced_lyrics: Optional[str]
    word_synced_lyrics: Optional[str]


class AlignmentAttempt(TypedDict):
    content: str
    source_type: Literal["plain", "synced"]
    source: str
    persist: bool


def _attempt_priority(attempt: AlignmentAttempt) -> tuple[int, int, str]:
    source_rank = 0 if attempt["source"].startswith("db:") else 1
    type_rank = 0 if attempt["source_type"] == "synced" else 1
    return (source_rank, type_rank, attempt["source"])


def select_initial_lyrics(attempts: list[AlignmentAttempt]) -> AlignmentAttempt | None:
    """Pick the best remote candidate to persist for immediate display."""
    remote_attempts = [attempt for attempt in attempts if not attempt["source"].startswith("db:")]
    if not remote_attempts:
        return None

    for source_type in ("synced", "plain"):
        for attempt in remote_attempts:
            if attempt["source_type"] == source_type:
                return attempt

    return None


def build_alignment_attempts(
    song: SongData,
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

    add_attempt(song["synced_lyrics"], "synced", "db:synced")
    add_attempt(song["plain_lyrics"], "plain", "db:plain")

    if not include_remote:
        return attempts

    track_name = (song["title"] or "").strip()
    artist_name = (song["artist"] or "").strip()
    if not track_name or not artist_name:
        return attempts

    from app.services.lyrics_service import LyricsService
    from app.services.syncedlyrics_service import SyncedLyricsService

    params = {
        "track_name": track_name,
        "artist_name": artist_name,
    }
    if song["album"]:
        params["album_name"] = song["album"]

    try:
        started_at = perf_counter()
        lrclib_results = LyricsService().search_lyrics_structured(params)
        log_lyrics_event(
            song["id"],
            "lyrics_remote_fetch_finished",
            provider="lrclib",
            elapsed_ms=round((perf_counter() - started_at) * 1000, 1),
            result_count=len(lrclib_results),
        )
        for idx, candidate in enumerate(lrclib_results[:max_remote_results]):
            add_attempt(
                candidate.get("syncedLyrics"),
                "synced",
                f"lrclib:{idx + 1}",
                persist=True,
            )
            add_attempt(
                candidate.get("plainLyrics"),
                "plain",
                f"lrclib:{idx + 1}",
                persist=True,
            )
    except Exception as e:
        log_lyrics_event(song["id"], "lyrics_remote_fetch_failed", provider="lrclib", exc_type=type(e).__name__)
        logger.debug(
            "LRCLIB candidate fetch failed for %s - %s",
            artist_name,
            track_name,
            exc_info=True,
        )

    try:
        started_at = perf_counter()
        synced_results = SyncedLyricsService().search_lyrics_structured(params)
        log_lyrics_event(
            song["id"],
            "lyrics_remote_fetch_finished",
            provider="syncedlyrics",
            elapsed_ms=round((perf_counter() - started_at) * 1000, 1),
            result_count=len(synced_results),
        )
        for idx, candidate in enumerate(synced_results[:max_remote_results]):
            add_attempt(
                candidate.get("syncedLyrics"),
                "synced",
                f"syncedlyrics:{idx + 1}",
                persist=True,
            )
            add_attempt(
                candidate.get("plainLyrics"),
                "plain",
                f"syncedlyrics:{idx + 1}",
                persist=True,
            )
    except Exception as e:
        log_lyrics_event(song["id"], "lyrics_remote_fetch_failed", provider="syncedlyrics", exc_type=type(e).__name__)
        logger.debug(
            "syncedlyrics candidate fetch failed for %s - %s",
            artist_name,
            track_name,
            exc_info=True,
        )

    return sorted(attempts, key=_attempt_priority)