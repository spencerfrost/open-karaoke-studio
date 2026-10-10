"""Tests for recording what an alignment run did about each lyrics report."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from app.db.models import DbSong, LyricsReport
from app.jobs.lyrics_tasks import _record_report_outcomes
from app.services.lyrics_retiming import lyrics_words_key

REPORTED = "[00:01.00]wrong words here"


@pytest.fixture
def song_with_report(test_db_session):
    test_db_session.add(
        DbSong(
            id="song-1", title="Blackbird", artist="The Beatles", synced_lyrics=REPORTED
        )
    )
    report = LyricsReport(
        song_id="song-1",
        kind="words",
        words_key=lyrics_words_key(REPORTED, "synced"),
        report_count=1,
    )
    test_db_session.add(report)
    test_db_session.commit()

    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=test_db_session)
    ctx.__exit__ = Mock(return_value=False)
    with patch("app.db.database.get_db_session", return_value=ctx):
        yield test_db_session, report


def _outcome(session, report, result, pending=None) -> str | None:
    _record_report_outcomes("song-1", result, pending or [(report.id, report.kind, 1)])
    session.refresh(report)
    return report.outcome


def test_other_lyrics_on_screen_means_replaced(song_with_report):
    session, report = song_with_report
    session.get(DbSong, "song-1").synced_lyrics = "[00:01.00]the right words"
    session.commit()

    assert (
        _outcome(session, report, {"status": "ok", "source": "lrclib:2"}) == "replaced"
    )


def test_the_same_words_newly_timed_means_retimed(song_with_report):
    session, report = song_with_report

    assert (
        _outcome(session, report, {"status": "retimed", "source": "db:synced"})
        == "retimed"
    )


def test_the_same_words_left_as_they_were_means_unchanged(song_with_report):
    session, report = song_with_report

    assert _outcome(session, report, {"status": "low_confidence"}) == "unchanged"


def test_an_asr_transcript_means_transcribed(song_with_report):
    session, report = song_with_report
    session.get(DbSong, "song-1").synced_lyrics = "[00:01.00]what asr heard"
    session.commit()

    assert (
        _outcome(session, report, {"status": "ok", "source": "asr:whisperx"})
        == "transcribed"
    )


def test_a_report_made_again_during_the_run_is_left_for_the_next_run(song_with_report):
    session, report = song_with_report
    report.report_count = 2
    session.commit()

    # The run started when the report had been made once.
    assert (
        _outcome(
            session,
            report,
            {"status": "low_confidence"},
            pending=[(report.id, "words", 1)],
        )
        is None
    )
