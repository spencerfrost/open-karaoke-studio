"""
Tests for unit 3b: lap computation, the (lap, seat, id) sort, and bump-to-next.

`test_lap_computation_matches_the_worked_example` walks the exact table from
docs/plans/archive/2026-08-29-roster-and-rotation.md's Stage 3b section - it is the
regression test for the mechanism and must not drift from that table.
"""

from datetime import datetime, timedelta

import pytest
from app.db.models import (
    DbSong,
    KaraokeQueueItem,
    KaraokeSession,
    SessionPlaybackState,
)
from app.services.queue_ordering import (
    advance_to,
    bump_to_next,
    compute_lap,
    enter_rotation,
    get_ordered_queue_items,
)
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


def _make_session(db, session_id="AAAA"):
    session = KaraokeSession(
        session_id=session_id,
        display_code=session_id,
        host_device_id=f"rest_{session_id.lower()}",
        host_user_id=HOST_USER_ID,
        expires_at=datetime.utcnow() + timedelta(hours=8),
        is_active=True,
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


def _add_item(db, session, performer, song_id, position):
    """Insert a queue item the way add_to_queue does: compute_lap, then a row."""
    lap = compute_lap(db, session, performer)
    enter_rotation(performer)
    item = KaraokeQueueItem(
        singer_name=performer.name,
        song_id=song_id,
        session_id=session.session_id,
        position=position,
        performer_id=performer.id,
        lap=lap,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ---------------------------------------------------------------------------
# Lap computation - the worked example
# ---------------------------------------------------------------------------


def test_lap_computation_matches_the_worked_example(db):
    """The plan doc's table, built the way it says it was built.

    Note the doc's table is in *play* order, not insert order - Spencer
    "queued 5 songs before anyone else touched a phone", so all five of his
    inserts happen first and the alternation is produced by the sort.
    """
    session = _make_session(db)
    _make_song(db)

    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    dan = resolve_or_create_performer(db, "AAAA", "Dan")
    db.commit()

    spencers = [_add_item(db, session, spencer, "test-song", i) for i in range(1, 6)]
    dans = [_add_item(db, session, dan, "test-song", i) for i in range(6, 11)]

    # Each performer's Nth song is their Nth turn - one burst of adds does not
    # push the next person to the back.
    assert [item.lap for item in spencers] == [0, 1, 2, 3, 4]
    assert [item.lap for item in dans] == [0, 1, 2, 3, 4]

    ordered = get_ordered_queue_items(db, "AAAA")
    assert [(item.singer_name, item.lap) for item in ordered[:5]] == [
        ("Spencer", 0),
        ("Dan", 0),
        ("Spencer", 1),
        ("Dan", 1),
        ("Spencer", 2),
    ]

    # Sarah walks up once playback has reached lap 2.
    session.current_lap = 2
    sarah = resolve_or_create_performer(db, "AAAA", "Sarah")
    db.commit()
    sarahs = _add_item(db, session, sarah, "test-song", 11)

    assert sarahs.lap == 2  # joins the circle where it is, no catch-up turns

    # Dan was queueing before Sarah walked up, so he precedes her in lap 2.
    lap_two = [item for item in get_ordered_queue_items(db, "AAAA") if item.lap == 2]
    assert [item.singer_name for item in lap_two] == ["Spencer", "Dan", "Sarah"]


def test_one_persons_burst_does_not_push_the_next_person_to_the_back(db):
    """Four songs as Jess, then three as Spencer, interleaves from the front.

    Two regressions in one: adding used to advance `current_lap` (so Spencer's
    first song landed at lap 3 behind all of Jess's), and the lap tie used to
    go to the lower seat (so Spencer, seated first as the host, opened every
    lap despite Jess having queued first).
    """
    session = _make_session(db)
    _make_song(db)

    # Spencer is on the roster first - he's the host, seated when the session
    # was created - but Jess is the first to actually queue anything.
    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    jess = resolve_or_create_performer(db, "AAAA", "Jess")
    db.commit()
    assert spencer.seat < jess.seat

    for i in range(1, 5):
        _add_item(db, session, jess, "test-song", i)
    for i in range(5, 8):
        _add_item(db, session, spencer, "test-song", i)

    assert session.current_lap == 0  # nothing has played, so nothing has moved
    ordered = get_ordered_queue_items(db, "AAAA")
    assert [item.singer_name for item in ordered] == [
        "Jess",
        "Spencer",
        "Jess",
        "Spencer",
        "Jess",
        "Spencer",
        "Jess",
    ]


def test_a_roster_entry_that_never_queues_does_not_take_a_place_in_the_circle(db):
    """Being on the roster is not being in the rotation - only queueing is."""
    session = _make_session(db)
    _make_song(db)

    bystander = resolve_or_create_performer(db, "AAAA", "Bystander")
    jess = resolve_or_create_performer(db, "AAAA", "Jess")
    db.commit()

    _add_item(db, session, jess, "test-song", 1)

    assert bystander.first_queued_at is None
    assert jess.first_queued_at is not None


def test_a_late_joiner_does_not_get_catch_up_turns(db):
    """Someone who arrives at lap 4 enters at lap 4, not with four turns owed."""
    session = _make_session(db)
    _make_song(db)

    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    db.commit()
    for i in range(1, 5):
        _add_item(db, session, spencer, "test-song", i)

    session.current_lap = 4  # the room has sung its way to lap 4
    late = resolve_or_create_performer(db, "AAAA", "Late Larry")
    db.commit()

    item = _add_item(db, session, late, "test-song", 5)
    assert item.lap == 4


def test_advance_to_moves_the_rotation_on_play(db):
    session = _make_session(db)
    _make_song(db)

    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    db.commit()
    first = _add_item(db, session, spencer, "test-song", 1)
    second = _add_item(db, session, spencer, "test-song", 2)

    advance_to(session, second)  # second song starts playing: lap 1
    db.commit()

    assert session.current_lap == 1
    assert spencer.laps_taken == 2  # his lap-1 turn is spent
    assert first.lap == 0  # existing rows are never rewritten


def test_a_singer_who_already_sang_this_lap_queues_into_the_next_one(db):
    session = _make_session(db)
    _make_song(db)

    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    db.commit()
    only = _add_item(db, session, spencer, "test-song", 1)

    advance_to(session, only)  # he sings it; laps_taken becomes 1
    db.commit()

    # His one row is still in the table as the current item, but it is no
    # longer pending, so his next song is lap 1 and not lap 2.
    playback = SessionPlaybackState(session_id="AAAA", current_queue_item_id=only.id)
    db.add(playback)
    db.commit()

    assert compute_lap(db, session, spencer) == 1


# ---------------------------------------------------------------------------
# Sort order
# ---------------------------------------------------------------------------


def test_rotation_mode_sorts_by_lap_then_entry_order(db):
    session = _make_session(db)
    _make_song(db)
    session.queue_order_mode = "rotation"
    db.commit()

    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    dan = resolve_or_create_performer(db, "AAAA", "Dan")
    db.commit()

    item1 = _add_item(db, session, spencer, "test-song", 1)
    item2 = _add_item(db, session, dan, "test-song", 2)
    item3 = _add_item(db, session, spencer, "test-song", 3)
    item4 = _add_item(db, session, dan, "test-song", 4)

    ordered = get_ordered_queue_items(db, "AAAA")
    assert [item.id for item in ordered] == [item1.id, item2.id, item3.id, item4.id]


def test_append_mode_sorts_by_position_ignoring_lap(db):
    session = _make_session(db)
    _make_song(db)
    session.queue_order_mode = "append"
    db.commit()

    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    dan = resolve_or_create_performer(db, "AAAA", "Dan")
    db.commit()

    # Both queued back to back, so both land on lap 0 - append mode must not
    # reorder them by anything lap-derived.
    item1 = _add_item(db, session, spencer, "test-song", 1)
    item2 = _add_item(db, session, spencer, "test-song", 2)
    item3 = _add_item(db, session, dan, "test-song", 3)

    ordered = get_ordered_queue_items(db, "AAAA")
    assert [item.id for item in ordered] == [item1.id, item2.id, item3.id]


# ---------------------------------------------------------------------------
# Bump to next
# ---------------------------------------------------------------------------


def test_bump_to_next_moves_an_item_ahead_of_everyone_pending(db):
    session = _make_session(db)
    _make_song(db)

    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    dan = resolve_or_create_performer(db, "AAAA", "Dan")
    db.commit()

    item1 = _add_item(db, session, spencer, "test-song", 1)
    item2 = _add_item(db, session, dan, "test-song", 2)
    item3 = _add_item(db, session, spencer, "test-song", 3)

    bumped = bump_to_next(db, "AAAA", item3.id)
    db.commit()

    assert bumped is not None
    assert bumped.lap < item1.lap
    ordered = get_ordered_queue_items(db, "AAAA")
    assert ordered[0].id == item3.id


def test_bump_to_next_returns_none_for_an_unknown_item(db):
    _make_session(db)
    assert bump_to_next(db, "AAAA", 999) is None


# ---------------------------------------------------------------------------
# API: add_to_queue writes a real lap
# ---------------------------------------------------------------------------


def test_playing_a_song_persists_the_advanced_rotation(client, db):
    """The play endpoint mutates the session row `require_session_owner`
    resolved - this asserts that write actually lands, rather than being made
    on a second Session and dropped."""
    _make_session(db)
    _make_song(db)

    for _ in range(2):
        client.post(
            "/api/karaoke-queue?session_code=AAAA",
            json={"singer": "Spencer", "songId": "test-song"},
        )
    second = db.query(KaraokeQueueItem).order_by(KaraokeQueueItem.id).all()[1]
    assert second.lap == 1

    response = client.post(f"/api/karaoke-queue/{second.id}/play?session_code=AAAA")
    assert response.status_code == 200

    db.expire_all()
    session = db.query(KaraokeSession).filter_by(session_id="AAAA").one()
    assert session.current_lap == 1
    assert second.performer.laps_taken == 2


def test_add_to_queue_writes_a_nonzero_lap_for_a_second_song(client, db):
    _make_session(db)
    _make_song(db)

    client.post(
        "/api/karaoke-queue?session_code=AAAA",
        json={"singer": "Spencer", "songId": "test-song"},
    )
    response = client.post(
        "/api/karaoke-queue?session_code=AAAA",
        json={"singer": "Spencer", "songId": "test-song"},
    )

    assert response.json()["lap"] == 1


# ---------------------------------------------------------------------------
# API: the queue-order-mode toggle
# ---------------------------------------------------------------------------


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
    session = _make_session(db)
    _make_song(db)
    session.queue_order_mode = "append"
    db.commit()

    add_response = client.post(
        "/api/karaoke-queue?session_code=AAAA",
        json={"singer": "Spencer", "songId": "test-song"},
    )
    item_id = add_response.json()["id"]

    response = client.post(f"/api/karaoke-queue/{item_id}/bump?session_code=AAAA")
    assert response.status_code == 400


def test_reorder_endpoint_requires_append_mode(client, db):
    session = _make_session(db)
    _make_song(db)
    session.queue_order_mode = "rotation"
    db.commit()

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
