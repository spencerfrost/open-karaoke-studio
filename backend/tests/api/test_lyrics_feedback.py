"""Tests for /api/lyrics/feedback: "How were the lyrics?" after each song."""

import json
import uuid
from datetime import timedelta

import pytest
from tests.api.conftest import _get_mock_requester

from app.api.dependencies import RequesterContext, require_host_or_session_member
from app.db.models import (
    DbSong,
    KaraokeQueueItem,
    KaraokeSession,
    LyricsFeedback,
    PerformanceHistory,
)
from app.utils.clock import utc_now

LYRICS = "[00:01.00]Blackbird singing in the dead of night"


@pytest.fixture(autouse=True)
def _restore_requester(fastapi_app):
    yield
    fastapi_app.dependency_overrides[require_host_or_session_member] = (
        _get_mock_requester
    )


def _as_guest_of(fastapi_app, session_id):
    fastapi_app.dependency_overrides[require_host_or_session_member] = (
        lambda: RequesterContext(session_id=session_id)
    )


def _sung_song(
    db, *, synced: str | None = LYRICS, aligned_at: str = "2026-10-28T12:00:00"
):
    """A session whose current queue item is a song that just finished."""
    session_id = uuid.uuid4().hex[:4].upper()
    song_id = f"song-{uuid.uuid4().hex[:8]}"
    db.add(
        KaraokeSession(
            session_id=session_id,
            display_code=session_id,
            host_device_id=f"rest_{session_id.lower()}",
            host_user_id=1,
            expires_at=utc_now() + timedelta(hours=8),
            is_active=True,
        )
    )
    db.add(
        DbSong(
            id=song_id,
            title="Blackbird",
            artist="The Beatles",
            duration=140,
            source="upload",
            synced_lyrics=synced,
            word_synced_lyrics=(
                json.dumps({"words": [], "aligned_at": aligned_at}) if synced else None
            ),
        )
    )
    db.flush()
    item = KaraokeQueueItem(
        singer_name="Sam", song_id=song_id, position=0, session_id=session_id
    )
    db.add(item)
    db.commit()
    return session_id, song_id, item.id


def _answer(client, item_id, rating):
    return client.post(
        "/api/lyrics/feedback", json={"queue_item_id": item_id, "rating": rating}
    )


def _summary_for(client, song_id):
    rows = client.get("/api/lyrics/feedback").json()
    return next(row for row in rows if row["songId"] == song_id)


def test_a_guest_answers_for_the_song_that_just_finished(client, fastapi_app, db):
    session_id, song_id, item_id = _sung_song(db)
    _as_guest_of(fastapi_app, session_id)

    resp = _answer(client, item_id, "way_off")

    assert resp.status_code == 200
    assert resp.json() == {"queueItemId": item_id, "rating": "way_off"}
    row = db.query(LyricsFeedback).filter_by(queue_item_id=item_id).one()
    assert row.song_id == song_id
    assert row.singer_name == "Sam"
    assert row.session_id == session_id
    assert row.word_timing_aligned_at == "2026-10-28T12:00:00"


def test_answering_again_replaces_the_answer(client, fastapi_app, db):
    session_id, _, item_id = _sung_song(db)
    _as_guest_of(fastapi_app, session_id)

    _answer(client, item_id, "way_off")
    _answer(client, item_id, "spot_on")

    rows = db.query(LyricsFeedback).filter_by(queue_item_id=item_id).all()
    assert [row.rating for row in rows] == ["spot_on"]


def test_a_guest_cant_answer_for_another_session(client, fastapi_app, db):
    _, _, item_id = _sung_song(db)
    other_session, _, _ = _sung_song(db)
    _as_guest_of(fastapi_app, other_session)

    assert _answer(client, item_id, "spot_on").status_code == 403


def test_a_song_that_left_the_queue_cant_be_answered(client):
    assert _answer(client, 999_999_999, "spot_on").status_code == 404


def test_a_song_without_lyrics_cant_be_answered(client, db):
    _, _, item_id = _sung_song(db, synced=None)

    assert _answer(client, item_id, "spot_on").status_code == 422


def test_only_known_ratings_are_accepted(client, db):
    _, _, item_id = _sung_song(db)

    assert _answer(client, item_id, "meh").status_code == 422


def test_the_summary_counts_answers_about_what_the_song_shows_now(client, db):
    session_id, song_id, first_item = _sung_song(db)
    _answer(client, first_item, "way_off")

    # The lyrics are re-timed: same words, new word timings.
    song = db.get(DbSong, song_id)
    song.word_synced_lyrics = json.dumps(
        {"words": [], "aligned_at": "2026-10-29T09:00:00"}
    )
    second_item = KaraokeQueueItem(
        singer_name="Alex", song_id=song_id, position=1, session_id=session_id
    )
    db.add(second_item)
    db.add(PerformanceHistory(song_id=song_id, singer_name="Sam"))
    db.add(PerformanceHistory(song_id=song_id, singer_name="Alex"))
    db.commit()
    _answer(client, second_item.id, "a_bit_off")

    summary = _summary_for(client, song_id)
    assert summary["wayOff"] == 0
    assert summary["aBitOff"] == 1
    assert summary["spotOn"] == 0
    assert summary["earlier"] == 1
    assert summary["plays"] == 2


def test_the_summary_lists_the_worst_songs_first(client, db):
    _, mild_song, mild_item = _sung_song(db)
    _, bad_song, bad_item = _sung_song(db)
    _answer(client, mild_item, "a_bit_off")
    _answer(client, bad_item, "way_off")

    order = [row["songId"] for row in client.get("/api/lyrics/feedback").json()]
    assert order.index(bad_song) < order.index(mild_song)


def test_only_admins_see_the_summary(client, fastapi_app):
    _as_guest_of(fastapi_app, "ZZZZ")
    from app.api.dependencies import get_current_user

    previous = fastapi_app.dependency_overrides[get_current_user]

    def _guest_user():
        user = previous()
        user.is_admin = False
        return user

    fastapi_app.dependency_overrides[get_current_user] = _guest_user
    try:
        assert client.get("/api/lyrics/feedback").status_code == 403
    finally:
        fastapi_app.dependency_overrides[get_current_user] = previous
