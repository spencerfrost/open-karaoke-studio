"""Tests for lyrics reports and the rejected lyrics they remember."""

from app.db.models import DbSong
from app.repositories.lyrics_report_repository import LyricsReportRepository


def _report(
    repo: LyricsReportRepository, *, kind="words", words_key="key-a", name="Sam"
):
    return repo.report(
        song_id="song-1",
        kind=kind,
        words_key=words_key,
        reporter_name=name,
        user_id=None,
        session_id=None,
    )


def _repo(test_db_session) -> LyricsReportRepository:
    test_db_session.add(DbSong(id="song-1", title="Blackbird", artist="The Beatles"))
    test_db_session.commit()
    return LyricsReportRepository(test_db_session)


def test_reporting_the_same_lyrics_again_counts_it_on_one_report(test_db_session):
    repo = _repo(test_db_session)

    first = _report(repo, name="Sam")
    second = _report(repo, name="Alex")

    assert second.id == first.id
    assert second.report_count == 2
    assert second.reporter_name == "Alex"
    assert len(repo.list_open()) == 1


def test_different_lyrics_or_kinds_are_separate_reports(test_db_session):
    repo = _repo(test_db_session)

    _report(repo, words_key="key-a")
    _report(repo, words_key="key-b")
    _report(repo, kind="timing", words_key="key-a")

    assert len(repo.list_open()) == 3


def test_only_wrong_words_reports_reject_lyrics_even_once_resolved(test_db_session):
    repo = _repo(test_db_session)

    words = _report(repo, words_key="rejected")
    _report(repo, kind="timing", words_key="just-out-of-sync")
    repo.resolve(words.id, user_id=None)

    assert repo.rejected_keys("song-1") == {"rejected"}
    assert [report.kind for report in repo.list_open()] == ["timing"]


def test_reporting_resolved_lyrics_again_reopens_the_report(test_db_session):
    repo = _repo(test_db_session)
    report = _report(repo)
    repo.set_outcome(report.id, "replaced")
    repo.resolve(report.id, user_id=None)

    reopened = _report(repo)

    assert reopened.id == report.id
    assert reopened.resolved_at is None
    assert reopened.outcome is None
    assert reopened.report_count == 2


def test_the_lyrics_kept_for_undo_are_from_the_first_report(test_db_session):
    repo = _repo(test_db_session)

    repo.report(
        song_id="song-1", kind="timing", words_key="same-words", reporter_name=None,
        user_id=None, session_id=None, synced_lyrics="[00:01.00]original timing",
    )
    report = repo.report(
        song_id="song-1", kind="timing", words_key="same-words", reporter_name=None,
        user_id=None, session_id=None, synced_lyrics="[00:03.00]after the first fix",
    )

    assert report.reported_synced_lyrics == "[00:01.00]original timing"
