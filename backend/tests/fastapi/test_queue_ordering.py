"""
Tests for queue ordering: the rotation projection, append mode, and the queue
endpoints that feed them.

Rotation mode is a circle of seats and a pointer (see
docs/plans/2026-09-25-rotation-circle.md). The play order is a projection:
start at the pointer, take each person's k-th song on the k-th pass. These
tests pin that walk; the pointer's movement is covered in test_turn.py.
"""

from datetime import datetime, timedelta

import pytest
from app.db.models import (
    DbSong,
    KaraokeQueueItem,
    KaraokeSession,
    SessionPlaybackState,
)
from app.services.queue_ordering import get_ordered_queue_items
from app.services.roster_service import resolve_or_create_performer
from tests.fastapi.conftest import _TestingSessionLocal

HOST_USER_ID = 1


@pytest.fixture
def db():
    session = _TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_session(db, session_id="AAAA", mode="rotation"):
    session = KaraokeSession(
        session_id=session_id,
        display_code=session_id,
        host_device_id=f"rest_{session_id.lower()}",
        host_user_id=HOST_USER_ID,
        expires_at=datetime.utcnow() + timedelta(hours=8),
        is_active=True,
        queue_order_mode=mode,
    )
    db.add(session)
    db.commit()
    return session


def _make_song(db, song_id="test-song"):
    song = DbSong(
        id=song_id,
        title="Test Song",
        artist="Test Artist",
        duration=180,
        source="upload",
    )
    db.add(song)
    db.commit()
    return song


def _add_item(db, session, performer, position=1, song_id="test-song"):
    """Insert a queue item the way add_to_queue does: no ordering data at all."""
    item = KaraokeQueueItem(
        singer_name=performer.name,
        song_id=song_id,
        session_id=session.session_id,
        position=position,
        performer_id=performer.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _people(db, *names):
    performers = [resolve_or_create_performer(db, "AAAA", name) for name in names]
    db.commit()
    return performers


def _order(db):
    return [item.id for item in get_ordered_queue_items(db, "AAAA")]


# ---------------------------------------------------------------------------
# The projection
# ---------------------------------------------------------------------------


def test_bursts_alternate_from_the_top(db):
    """Two people queue 5 and 3 songs in bursts - the order still alternates."""
    session = _make_session(db)
    _make_song(db)
    spencer, dan = _people(db, "Spencer", "Dan")

    spencers = [_add_item(db, session, spencer) for _ in range(5)]
    dans = [_add_item(db, session, dan) for _ in range(3)]

    s, d = [i.id for i in spencers], [i.id for i in dans]
    assert _order(db) == [s[0], d[0], s[1], d[1], s[2], d[2], s[3], s[4]]


def test_order_within_a_lap_is_seat_order_not_queue_order(db):
    """Dan queued first, but Spencer holds the lower seat."""
    session = _make_session(db)
    _make_song(db)
    spencer, dan = _people(db, "Spencer", "Dan")

    dans = _add_item(db, session, dan)
    spencers = _add_item(db, session, spencer)

    assert _order(db) == [spencers.id, dans.id]


def test_projection_starts_at_the_pointer(db):
    session = _make_session(db)
    _make_song(db)
    spencer, dan, sarah = _people(db, "Spencer", "Dan", "Sarah")
    items = {p.id: _add_item(db, session, p).id for p in (spencer, dan, sarah)}

    session.turn_performer_id = dan.id
    db.commit()

    assert _order(db) == [items[dan.id], items[sarah.id], items[spencer.id]]


def test_someone_with_nothing_queued_gives_up_no_place(db):
    """An empty seat is a turn, not a song - the list just moves past it."""
    session = _make_session(db)
    _make_song(db)
    spencer, patrick, sarah = _people(db, "Spencer", "Patrick", "Sarah")
    a = _add_item(db, session, spencer)
    b = _add_item(db, session, sarah)

    assert _order(db) == [a.id, b.id]


def test_the_playing_item_leads_and_is_not_projected(db):
    session = _make_session(db)
    _make_song(db)
    spencer, dan = _people(db, "Spencer", "Dan")
    playing = _add_item(db, session, dan)
    spencers = _add_item(db, session, spencer)
    db.add(SessionPlaybackState(session_id="AAAA", current_queue_item_id=playing.id))
    db.commit()

    assert _order(db) == [playing.id, spencers.id]


def test_borrowed_turn_is_stepped_over_once(db):
    session = _make_session(db)
    _make_song(db)
    spencer, dan, sarah = _people(db, "Spencer", "Dan", "Sarah")
    s1, s2 = _add_item(db, session, spencer), _add_item(db, session, spencer)
    d1, d2 = _add_item(db, session, dan), _add_item(db, session, dan)
    r1, r2 = _add_item(db, session, sarah), _add_item(db, session, sarah)

    dan.turns_borrowed = 1
    db.commit()

    # Lap 1 skips Dan; lap 2 is everyone; Dan's second song trails on its own.
    assert _order(db) == [s1.id, r1.id, s2.id, d1.id, r2.id, d2.id]


def test_bumped_song_goes_first_and_costs_that_persons_next_turn(db):
    session = _make_session(db)
    _make_song(db)
    spencer, dan, sarah = _people(db, "Spencer", "Dan", "Sarah")
    s1, s2 = _add_item(db, session, spencer), _add_item(db, session, spencer)
    d1, d2 = _add_item(db, session, dan), _add_item(db, session, dan)
    r1 = _add_item(db, session, sarah)

    session.bumped_item_id = d2.id
    db.commit()

    # d2 now, then the pointer resumes at Spencer and steps over Dan once.
    assert _order(db) == [d2.id, s1.id, r1.id, s2.id, d1.id]


def test_holders_own_bump_is_their_real_turn(db):
    session = _make_session(db)
    _make_song(db)
    spencer, dan = _people(db, "Spencer", "Dan")
    s1, s2 = _add_item(db, session, spencer), _add_item(db, session, spencer)
    d1 = _add_item(db, session, dan)

    session.bumped_item_id = s2.id
    db.commit()

    assert _order(db) == [s2.id, d1.id, s1.id]


def test_removed_performers_songs_are_hidden_not_deleted(db):
    session = _make_session(db)
    _make_song(db)
    spencer, dan = _people(db, "Spencer", "Dan")
    s1 = _add_item(db, session, spencer)
    d1 = _add_item(db, session, dan)

    dan.is_active = False
    db.commit()

    assert _order(db) == [s1.id]
    assert db.get(KaraokeQueueItem, d1.id) is not None


def test_rows_without_a_performer_trail_the_circle(db):
    session = _make_session(db)
    _make_song(db)
    (spencer,) = _people(db, "Spencer")
    ghost = KaraokeQueueItem(
        singer_name="Ghost", song_id="test-song", session_id="AAAA", position=1
    )
    db.add(ghost)
    db.commit()
    s1 = _add_item(db, session, spencer)

    assert _order(db) == [s1.id, ghost.id]


def test_append_mode_sorts_by_position(db):
    session = _make_session(db, mode="append")
    _make_song(db)
    spencer, dan = _people(db, "Spencer", "Dan")

    item1 = _add_item(db, session, spencer, position=1)
    item2 = _add_item(db, session, spencer, position=2)
    item3 = _add_item(db, session, dan, position=3)

    assert _order(db) == [item1.id, item2.id, item3.id]


def test_append_mode_ignores_the_circle(db):
    """Removed people, bumps and borrowed turns only mean anything in rotation."""
    session = _make_session(db, mode="append")
    _make_song(db)
    spencer, dan = _people(db, "Spencer", "Dan")
    item1 = _add_item(db, session, spencer, position=1)
    item2 = _add_item(db, session, dan, position=2)

    dan.is_active = False
    session.bumped_item_id = item2.id
    db.commit()

    assert _order(db) == [item1.id, item2.id]


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_queue_payload_no_longer_carries_a_lap(client, db):
    _make_session(db)
    _make_song(db)

    response = client.post(
        "/api/karaoke-queue?session_code=AAAA",
        json={"singer": "Spencer", "songId": "test-song"},
    )
    assert response.status_code == 201
    assert "lap" not in response.json()

    state = client.get("/api/karaoke-queue?session_code=AAAA").json()
    assert "lap" not in state["upcoming"][0]


def test_bump_endpoint_makes_the_song_next(client, db):
    session = _make_session(db)
    _make_song(db)
    spencer, dan = _people(db, "Spencer", "Dan")
    _add_item(db, session, spencer)
    dans = _add_item(db, session, dan)

    response = client.post(f"/api/karaoke-queue/{dans.id}/bump?session_code=AAAA")
    assert response.status_code == 200

    db.expire_all()
    assert db.get(KaraokeSession, session.id).bumped_item_id == dans.id
    assert _order(db)[0] == dans.id


def test_bump_endpoint_rejects_the_playing_song(client, db):
    session = _make_session(db)
    _make_song(db)
    (spencer,) = _people(db, "Spencer")
    playing = _add_item(db, session, spencer)
    db.add(SessionPlaybackState(session_id="AAAA", current_queue_item_id=playing.id))
    db.commit()

    response = client.post(f"/api/karaoke-queue/{playing.id}/bump?session_code=AAAA")
    assert response.status_code == 400


def test_bump_endpoint_returns_404_for_an_unknown_item(client, db):
    _make_session(db)
    response = client.post("/api/karaoke-queue/999/bump?session_code=AAAA")
    assert response.status_code == 404


def test_set_queue_order_mode_updates_the_session(client, db):
    _make_session(db)

    response = client.patch(
        "/api/sessions/AAAA/queue-order-mode", json={"mode": "append"}
    )

    assert response.status_code == 200
    assert response.json()["queue_order_mode"] == "append"
    db.expire_all()
    assert (
        db.query(KaraokeSession).filter_by(session_id="AAAA").one().queue_order_mode
        == "append"
    )


def test_set_queue_order_mode_rejects_an_invalid_mode(client, db):
    _make_session(db)

    response = client.patch(
        "/api/sessions/AAAA/queue-order-mode", json={"mode": "shuffle"}
    )

    assert response.status_code == 400


def test_bump_endpoint_requires_rotation_mode(client, db):
    _make_session(db, mode="append")
    _make_song(db)

    add_response = client.post(
        "/api/karaoke-queue?session_code=AAAA",
        json={"singer": "Spencer", "songId": "test-song"},
    )
    item_id = add_response.json()["id"]

    response = client.post(f"/api/karaoke-queue/{item_id}/bump?session_code=AAAA")
    assert response.status_code == 400


def test_reorder_endpoint_requires_append_mode(client, db):
    _make_session(db)
    _make_song(db)

    add_response = client.post(
        "/api/karaoke-queue?session_code=AAAA",
        json={"singer": "Spencer", "songId": "test-song"},
    )
    item_id = add_response.json()["id"]

    response = client.put(
        "/api/karaoke-queue/reorder?session_code=AAAA",
        json={"queue": [{"id": item_id, "position": 1}]},
    )
    assert response.status_code == 400
