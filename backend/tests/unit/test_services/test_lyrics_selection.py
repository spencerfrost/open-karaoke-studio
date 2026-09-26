from unittest.mock import MagicMock, patch

from app.services.lyrics_selection import build_alignment_attempts


def make_song(**overrides):
    data = {
        "id": "song-1",
        "title": "Test Song",
        "artist": "Test Artist",
        "album": "Test Album",
        "plain_lyrics": "db plain",
        "synced_lyrics": "[00:00.00]db synced",
        "word_synced_lyrics": None,
    }
    data.update(overrides)
    return data


def test_build_alignment_attempts_prefers_db_synced_then_db_plain():
    attempts = build_alignment_attempts(make_song(), include_remote=False)

    assert [attempt["source"] for attempt in attempts] == ["db:synced", "db:plain"]
    assert [attempt["source_type"] for attempt in attempts] == ["synced", "plain"]


def test_build_alignment_attempts_adds_remote_synced_before_remote_plain():
    with patch("app.services.lyrics_service.LyricsService") as mock_lrclib_cls, patch(
        "app.services.syncedlyrics_service.SyncedLyricsService"
    ) as mock_synced_cls:
        mock_lrclib = MagicMock()
        mock_lrclib.search_lyrics_structured.return_value = [
            {"plainLyrics": "lrclib plain", "syncedLyrics": "[00:00.00]lrclib synced"}
        ]
        mock_lrclib_cls.return_value = mock_lrclib

        mock_synced = MagicMock()
        mock_synced.search_lyrics_structured.return_value = [
            {"plainLyrics": "synced plain", "syncedLyrics": "[00:00.00]synced synced"}
        ]
        mock_synced_cls.return_value = mock_synced

        attempts = build_alignment_attempts(
            make_song(plain_lyrics=None, synced_lyrics=None),
            include_remote=True,
        )

    # Attempts are ordered synced-type first, then plain-type; within a type
    # they are sorted by source name ("lrclib:1" < "syncedlyrics:1").
    assert [attempt["source"] for attempt in attempts] == [
        "lrclib:1",
        "syncedlyrics:1",
        "lrclib:1",
        "syncedlyrics:1",
    ]
    assert [attempt["source_type"] for attempt in attempts] == [
        "synced",
        "synced",
        "plain",
        "plain",
    ]


def test_build_alignment_attempts_deduplicates_same_content_per_source_type():
    with patch("app.services.lyrics_service.LyricsService") as mock_lrclib_cls, patch(
        "app.services.syncedlyrics_service.SyncedLyricsService"
    ) as mock_synced_cls:
        mock_lrclib = MagicMock()
        mock_lrclib.search_lyrics_structured.return_value = [
            {"plainLyrics": "shared plain", "syncedLyrics": "[00:00.00]shared synced"}
        ]
        mock_lrclib_cls.return_value = mock_lrclib

        mock_synced = MagicMock()
        mock_synced.search_lyrics_structured.return_value = [
            {"plainLyrics": "shared plain", "syncedLyrics": "[00:00.00]shared synced"}
        ]
        mock_synced_cls.return_value = mock_synced

        attempts = build_alignment_attempts(
            make_song(plain_lyrics=None, synced_lyrics=None),
            include_remote=True,
        )

    assert len(attempts) == 2
    assert [attempt["source_type"] for attempt in attempts] == ["synced", "plain"]