"""Tests for the library-wide lyrics alignment run: one align_song_lyrics job per song."""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from app.jobs.batch_tasks import batch_align_lyrics


def _song(song_id, title):
    return SimpleNamespace(id=song_id, title=title, artist="Queen")


def _run(selected, *, with_vocals, dispatched):
    session_ctx = MagicMock()
    session_ctx.__enter__ = Mock(return_value=Mock())
    session_ctx.__exit__ = Mock(return_value=False)
    with (
        patch("app.db.database.get_db_session", return_value=session_ctx),
        patch(
            "app.services.lyrics_repair.select_songs_for_alignment",
            return_value=(selected, with_vocals),
        ) as mock_select,
        patch(
            "app.jobs.lyrics_dispatch.enqueue_song_alignment",
            side_effect=lambda song, **_: {"dispatched": dispatched[song.id]},
        ) as mock_enqueue,
    ):
        result = batch_align_lyrics.run(mode="repair")
    return result, mock_select, mock_enqueue


def test_each_selected_song_is_queued_as_its_own_alignment_job():
    selected = [
        (_song("a", "Bohemian Rhapsody"), ["no_word_timing"]),
        (_song("b", "Somebody to Love"), ["words_mismatch", "reported"]),
    ]

    result, mock_select, mock_enqueue = _run(
        selected, with_vocals=10, dispatched={"a": True, "b": True}
    )

    assert mock_select.call_args.args[1] == "repair"
    assert [call.args[0].id for call in mock_enqueue.call_args_list] == ["a", "b"]
    assert all(
        call.kwargs == {"include_remote": True} for call in mock_enqueue.call_args_list
    )
    assert result["selected"] == 2
    assert result["queued"] == 2
    assert result["alreadyRunning"] == 0
    assert result["skipped"] == 8
    assert result["reasons"]["words_mismatch"] == 1
    assert result["results"][1] == {
        "songId": "b",
        "title": "Queen — Somebody to Love",
        "status": "queued",
        "reasons": ["words_mismatch", "reported"],
    }


def test_a_song_already_aligning_is_not_queued_twice():
    selected = [(_song("a", "Bohemian Rhapsody"), ["no_word_timing"])]

    result, _, _ = _run(selected, with_vocals=1, dispatched={"a": False})

    assert result["queued"] == 0
    assert result["alreadyRunning"] == 1
    assert result["results"][0]["status"] == "already_running"
