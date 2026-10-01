"""Tests that stored word timings always match the lyrics text stored beside them."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.jobs.lyrics_tasks import align_song_lyrics
from app.services.lyrics_analysis import parse_lrc_lines

SONG_ID = "song-lyrics-storage-123"
DB_LRC = "[00:10.00]old words here\n[00:13.00]from the database"
# A 24s gap after the third line: formatting inserts a blank break line there.
REMOTE_LRC = "\n".join(
    [
        "[00:10.00]first line of verse",
        "[00:13.00]second line keeps going",
        "[00:16.00]third line of verse",
        "[00:40.00]after the guitar break",
        "[00:43.00]and the last line",
    ]
)


def _make_db_context(mock_session):
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=mock_session)
    ctx.__exit__ = Mock(return_value=False)
    return ctx


def _alignment_for(lrc: str, mean_score: float, *, line_index_shift: int = 0) -> dict:
    """Alignment whose words read as `lrc`, numbered the way the aligner numbers them."""
    words = []
    for line_index, line in enumerate(parse_lrc_lines(lrc)):
        for token in line["text"].split():
            words.append(
                {
                    "word": token,
                    "start": line["timestamp"] + len(words) * 0.1,
                    "end": line["timestamp"] + len(words) * 0.1 + 0.1,
                    "score": mean_score,
                    "line_index": line_index + line_index_shift,
                }
            )
    return {
        "words": words,
        "instrumental_intervals": [],
        "language": "en",
        "aligned_at": "2026-09-30T00:00:00+00:00",
        "word_count": len(words),
        "line_count": len([line for line in parse_lrc_lines(lrc) if line["text"].strip()]),
        "mean_score": mean_score,
    }


def _stored_line_texts(song) -> dict[int, list[str]]:
    """Map each stored word's line_index to the words on that line of the stored LRC."""
    lines = parse_lrc_lines(song.synced_lyrics)
    stored = json.loads(song.word_synced_lyrics)
    return {word["line_index"]: lines[word["line_index"]]["text"].split() for word in stored["words"]}


@pytest.fixture
def task_env():
    song = SimpleNamespace(
        id=SONG_ID,
        title="Test Song",
        artist="Test Artist",
        album=None,
        plain_lyrics=None,
        synced_lyrics=DB_LRC,
        word_synced_lyrics=None,
        lyrics_hand_picked_at=None,
        language="en",
    )
    mock_session = MagicMock()
    mock_repo = MagicMock()
    mock_repo.fetch.return_value = song

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("app.config.get_config", return_value=SimpleNamespace(BASE_LIBRARY_DIR="/karaoke-library")),
        patch("app.db.database.get_db_session", return_value=_make_db_context(mock_session)),
        patch("app.repositories.song_repository.SongRepository", return_value=mock_repo),
        patch("app.jobs.lyrics_tasks.job_repository") as mock_job_repository,
        patch("app.jobs.lyrics_tasks._build_alignment_attempts") as mock_build_attempts,
        patch("app.jobs.lyrics_tasks.run_alignment_attempt") as mock_run_alignment,
        patch("app.jobs.lyrics_tasks.log_lyrics_event") as mock_log,
        patch("app.jobs.lyrics_tasks._update_lyrics_alignment_job"),
        patch("app.jobs.lyrics_tasks._complete_lyrics_alignment_job"),
        patch("app.services.lyrics_offset.sweep_lrc_offset", return_value=None),
        patch("app.services.lyrics_transcription.transcribe_lyrics_from_vocals", return_value=None) as mock_transcribe,
    ):
        mock_job_repository.get_by_id.return_value = None
        yield SimpleNamespace(
            song=song,
            build_attempts=mock_build_attempts,
            run_alignment=mock_run_alignment,
            transcribe=mock_transcribe,
            log=mock_log,
        )


def _logged_events(mock_log) -> list[str]:
    return [call.args[1] for call in mock_log.call_args_list]


def test_a_later_candidate_that_aligns_replaces_the_stored_lyrics(task_env):
    task_env.build_attempts.return_value = [
        {"content": DB_LRC, "source_type": "synced", "source": "db:synced", "persist": False},
        {"content": REMOTE_LRC, "source_type": "synced", "source": "lrclib:2", "persist": True},
    ]
    # The aligner sees the formatted remote LRC; number its words against that.
    task_env.run_alignment.side_effect = lambda *, attempt, **_: (
        _alignment_for(DB_LRC, 0.1) if attempt["source"] == "db:synced" else _alignment_for(attempt["content"], 0.8)
    )

    result = align_song_lyrics(SONG_ID)

    assert result == {"status": "ok", "song_id": SONG_ID, "source": "lrclib:2"}
    assert "after the guitar break" in task_env.song.synced_lyrics
    assert "old words here" not in task_env.song.synced_lyrics
    stored = json.loads(task_env.song.word_synced_lyrics)
    assert stored["lyrics_source"] == "lrclib:2"
    for line_index, line_words in _stored_line_texts(task_env.song).items():
        assert [w["word"] for w in stored["words"] if w["line_index"] == line_index] == line_words


def test_every_synced_candidate_is_formatted_before_it_is_aligned(task_env):
    task_env.build_attempts.return_value = [
        {"content": DB_LRC, "source_type": "synced", "source": "db:synced", "persist": False},
        {"content": REMOTE_LRC, "source_type": "synced", "source": "lrclib:2", "persist": True},
    ]
    task_env.run_alignment.side_effect = lambda *, attempt, **_: _alignment_for(attempt["content"], 0.1)

    align_song_lyrics(SONG_ID)

    aligned_remote = task_env.run_alignment.call_args_list[1].kwargs["attempt"]["content"]
    assert len(aligned_remote.splitlines()) == len(REMOTE_LRC.splitlines()) + 1
    assert [line["text"] for line in parse_lrc_lines(aligned_remote)][3] == ""


def test_words_that_do_not_read_as_the_candidate_text_are_not_stored(task_env):
    task_env.build_attempts.return_value = [
        {"content": DB_LRC, "source_type": "synced", "source": "db:synced", "persist": False},
        {"content": REMOTE_LRC, "source_type": "synced", "source": "lrclib:1", "persist": True},
    ]
    # db:synced scores well, but its words are another version of the lyrics.
    task_env.run_alignment.side_effect = lambda *, attempt, **_: (
        _alignment_for("[00:10.00]different words entirely here", 0.9)
        if attempt["source"] == "db:synced"
        else _alignment_for(attempt["content"], 0.8)
    )

    result = align_song_lyrics(SONG_ID)

    assert result["source"] == "lrclib:1"
    assert "lyrics_words_mismatch" in _logged_events(task_env.log)
    assert json.loads(task_env.song.word_synced_lyrics)["lyrics_source"] == "lrclib:1"


def test_words_pointing_at_the_wrong_line_are_renumbered_before_storing(task_env):
    task_env.build_attempts.return_value = [
        {"content": DB_LRC, "source_type": "synced", "source": "db:synced", "persist": False},
    ]
    # Right words, but every word points one line down (the old sentence-split bug).
    task_env.run_alignment.return_value = _alignment_for(DB_LRC, 0.8, line_index_shift=1)

    align_song_lyrics(SONG_ID)

    stored = json.loads(task_env.song.word_synced_lyrics)
    assert [w["line_index"] for w in stored["words"]] == [0, 0, 0, 1, 1, 1]
    assert "lyrics_words_relabelled" in _logged_events(task_env.log)


def test_asr_words_point_at_the_formatted_transcript(task_env):
    task_env.build_attempts.return_value = []
    asr_lrc = REMOTE_LRC
    task_env.transcribe.return_value = {
        "plain_lyrics": "\n".join(line["text"] for line in parse_lrc_lines(asr_lrc)),
        "synced_lyrics": asr_lrc,
        "alignment": _alignment_for(asr_lrc, 0.7),
    }

    result = align_song_lyrics(SONG_ID)

    assert result["status"] == "ok"
    # Formatting added a break line before "after the guitar break".
    lines = parse_lrc_lines(task_env.song.synced_lyrics)
    assert lines[3]["text"] == ""
    stored = json.loads(task_env.song.word_synced_lyrics)
    after_break = [w for w in stored["words"] if w["word"] == "after"]
    assert after_break[0]["line_index"] == 4
    for line_index, line_words in _stored_line_texts(task_env.song).items():
        assert [w["word"] for w in stored["words"] if w["line_index"] == line_index] == line_words


def test_asr_lyrics_are_kept_without_word_timings_when_the_words_do_not_match(task_env):
    task_env.build_attempts.return_value = []
    task_env.transcribe.return_value = {
        "plain_lyrics": "hello world",
        "synced_lyrics": "[00:01.00]hello world",
        "alignment": _alignment_for("[00:01.00]goodbye moon", 0.7),
    }

    result = align_song_lyrics(SONG_ID)

    assert result["status"] == "ok"
    assert task_env.song.synced_lyrics == "[00:01.00]hello world"
    assert task_env.song.word_synced_lyrics is None
