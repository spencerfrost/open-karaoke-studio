"""
Tests for the turn: the circle, the pointer, and everything that moves it.

The cases follow docs/plans/2026-09-25-rotation-circle.md's verification list:
walk-ups, skip without back-to-back songs, add performer at the pointer, phone
joins, remove and undo, songs played out of order, bump mid-song, and append
mode being unaffected by any of it.
"""

from datetime import datetime, timedelta

import pytest
from app.db.models import (
    DbSong,
    KaraokeQueueItem,
    KaraokeSession,
    SessionPerformer,
    SessionPlaybackState,
)
from app.services import turn_service
from app.services.queue_ordering import get_ordered_queue_items
from app.services.roster_service import resolve_or_create_performer
from app.services.turn_service import (
    KIND_EMPTY_SEAT,
    KIND_OPEN,
    KIND_QUEUED,
    compute_turn,
    serialize_turn,
)
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


def _people(db, *names):
    performers = [resolve_or_create_performer(db, "AAAA", name) for name in names]
    db.commit()
    return performers


def _add_item(db, session, performer, position=1):
    item = KaraokeQueueItem(
        singer_name=performer.name,
        song_id="test-song",
        session_id=session.session_id,
        position=position,
        performer_id=performer.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _play(db, session, item):
    """What /play does to the rotation: the previous song leaves, this one
    becomes current, and the turn is recorded."""
    state = db.query(SessionPlaybackState).filter_by(session_id="AAAA").first()
    if state is None:
        state = SessionPlaybackState(session_id="AAAA")
        db.add(state)
    elif state.current_queue_item_id is not None:
        previous = db.get(KaraokeQueueItem, state.current_queue_item_id)
        if previous is not None and previous.id != item.id:
            db.delete(previous)
    state.current_queue_item_id = item.id
    turn_service.record_play(db, session, item)
    db.commit()


def _play_next(db, session):
    """Play whatever the turn says - the handoff screen's Enter."""
    turn = compute_turn(db, "AAAA")
    assert turn.kind == KIND_QUEUED, turn
    _play(db, session, turn.item)
    return turn


def _holder(db):
    return compute_turn(db, "AAAA").performer


def _singers(db, session, count):
    """Who sings the next `count` songs, playing each one in turn."""
    return [_play_next(db, session).performer.name for _ in range(count)]


# ---------------------------------------------------------------------------
# compute_turn - the three kinds
# ---------------------------------------------------------------------------


def test_turn_is_the_holders_first_song(db):
    session = _make_session(db)
    _make_song(db)
    spencer, dan = _people(db, "Spencer", "Dan")
    _add_item(db, session, dan)
    spencers = _add_item(db, session, spencer)

    turn = compute_turn(db, "AAAA")
    assert turn.kind == KIND_QUEUED
    assert turn.performer.id == spencer.id
    assert turn.item.id == spencers.id


def test_walk_up_is_an_empty_seat_even_with_others_queued(db):
    """The pointer is on Patrick with nothing queued: name him and wait."""
    session = _make_session(db)
    _make_song(db)
    spencer, patrick = _people(db, "Spencer", "Patrick")
    _add_item(db, session, spencer)
    session.turn_performer_id = patrick.id
    db.commit()

    turn = compute_turn(db, "AAAA")
    assert turn.kind == KIND_EMPTY_SEAT
    assert turn.performer.id == patrick.id
    assert turn.item is None


def test_empty_seat_every_lap_until_they_pick(db):
    session = _make_session(db)
    _make_song(db)
    spencer, patrick = _people(db, "Spencer", "Patrick")
    for _ in range(3):
        _add_item(db, session, spencer)

    for _ in range(3):
        assert _play_next(db, session).performer.id == spencer.id
        turn = compute_turn(db, "AAAA")
        assert turn.kind == KIND_EMPTY_SEAT
        assert turn.performer.id == patrick.id
        # Patrick walks up, browses, and picks nothing this time.
        turn_service.skip(db, session, turn)
        db.commit()


def test_empty_roster_is_open(db):
    _make_session(db)
    turn = compute_turn(db, "AAAA")
    assert turn.kind == KIND_OPEN
    assert turn.performer is None
    assert turn.circle == []


def test_circle_starts_at_the_holder(db):
    session = _make_session(db)
    spencer, dan, sarah = _people(db, "Spencer", "Dan", "Sarah")
    session.turn_performer_id = dan.id
    db.commit()

    circle = serialize_turn(compute_turn(db, "AAAA"))["circle"]
    assert [p["id"] for p in circle] == [dan.id, sarah.id, spencer.id]


def test_serialize_falls_back_to_singer_name_for_pre_roster_rows(db):
    """Legacy rows have no performer_id; the screen still needs a name."""
    _make_session(db)
    _make_song(db)
    item = KaraokeQueueItem(
        singer_name="Ghost", song_id="test-song", session_id="AAAA", position=1
    )
    db.add(item)
    db.commit()

    payload = serialize_turn(compute_turn(db, "AAAA"))
    assert payload["performerName"] == "Ghost"
    assert payload["performerId"] is None
    assert payload["itemId"] == item.id


# ---------------------------------------------------------------------------
# Playing songs
# ---------------------------------------------------------------------------


def test_playing_the_holders_song_passes_the_turn(db):
    session = _make_session(db)
    _make_song(db)
    spencer, dan = _people(db, "Spencer", "Dan")
    _add_item(db, session, spencer)

    _play_next(db, session)

    turn = compute_turn(db, "AAAA")
    assert turn.kind == KIND_EMPTY_SEAT
    assert turn.performer.id == dan.id


def test_the_pointer_wraps_at_the_end_of_the_lap(db):
    session = _make_session(db)
    _make_song(db)
    spencer, dan = _people(db, "Spencer", "Dan")
    for _ in range(2):
        _add_item(db, session, spencer)
        _add_item(db, session, dan)

    assert _singers(db, session, 4) == ["Spencer", "Dan", "Spencer", "Dan"]


def test_solo_singer_comes_straight_back_round(db):
    session = _make_session(db)
    _make_song(db)
    (spencer,) = _people(db, "Spencer")
    _add_item(db, session, spencer)

    _play_next(db, session)

    turn = compute_turn(db, "AAAA")
    assert turn.kind == KIND_EMPTY_SEAT
    assert turn.performer.id == spencer.id


def test_playing_out_of_order_moves_nobody_else(db):
    """The old lap model jumped the room forward here. Dan borrows his next
    turn instead; Patrick, who has nothing queued, keeps his."""
    session = _make_session(db)
    _make_song(db)
    spencer, dan, patrick, sarah = _people(db, "Spencer", "Dan", "Patrick", "Sarah")
    _add_item(db, session, spencer)
    dans = _add_item(db, session, dan)
    _add_item(db, session, dan)
    _add_item(db, session, sarah)
    session.turn_performer_id = patrick.id
    db.commit()

    # From the queue rail, the host plays Dan's song while it's Patrick's turn.
    _play(db, session, dans)

    assert _holder(db).id == patrick.id
    turn_service.skip(db, session, compute_turn(db, "AAAA"))
    db.commit()
    # Sarah, Spencer, then the pointer steps over Dan once and it's Patrick.
    assert _singers(db, session, 2) == ["Sarah", "Spencer"]
    assert _holder(db).id == patrick.id
    assert dan.turns_borrowed == 0
    # Next lap nobody but Dan has a song; walking the empty seats reaches him.
    for _ in range(3):  # Patrick, Sarah, Spencer
        turn_service.skip(db, session, compute_turn(db, "AAAA"))
        db.commit()
    assert _singers(db, session, 1) == ["Dan"]


def test_bump_during_a_song_then_the_pointer_resumes(db):
    session = _make_session(db)
    _make_song(db)
    spencer, dan, sarah = _people(db, "Spencer", "Dan", "Sarah")
    spencers = _add_item(db, session, spencer)
    _add_item(db, session, dan)
    sarahs = _add_item(db, session, sarah)

    _play_next(db, session)  # Spencer is singing; Dan is up next.
    session.bumped_item_id = sarahs.id
    db.commit()

    turn = compute_turn(db, "AAAA")
    assert turn.item.id == sarahs.id
    assert get_ordered_queue_items(db, "AAAA")[0].id == spencers.id  # current

    _play_next(db, session)
    assert session.bumped_item_id is None
    # The pointer never left Dan; Sarah's borrowed turn is spent when it
    # reaches her, so Spencer follows Dan.
    assert _holder(db).id == dan.id
    _add_item(db, session, spencer)
    assert _singers(db, session, 2) == ["Dan", "Spencer"]


# ---------------------------------------------------------------------------
# Skip
# ---------------------------------------------------------------------------


def test_skip_with_songs_in_consecutive_laps_is_not_back_to_back(db):
    """The lap-model bug: Sarah's two songs both landed in lap 3."""
    session = _make_session(db)
    _make_song(db)
    sarah, dan = _people(db, "Sarah", "Dan")
    _add_item(db, session, sarah)
    _add_item(db, session, sarah)
    _add_item(db, session, dan)
    _add_item(db, session, dan)

    turn_service.skip(db, session, compute_turn(db, "AAAA"))
    db.commit()

    assert _singers(db, session, 4) == ["Dan", "Sarah", "Dan", "Sarah"]


def test_skip_never_takes_anyone_out_of_the_rotation(db):
    session = _make_session(db)
    sarah, dan = _people(db, "Sarah", "Dan")

    for _ in range(5):
        turn_service.skip(db, session, compute_turn(db, "AAAA"))
        db.commit()

    assert sarah.is_active and dan.is_active
    assert _holder(db).id == dan.id


def test_skipping_someone_elses_bump_returns_the_turn_to_the_holder(db):
    session = _make_session(db)
    _make_song(db)
    spencer, dan = _people(db, "Spencer", "Dan")
    spencers = _add_item(db, session, spencer)
    dans = _add_item(db, session, dan)
    session.bumped_item_id = dans.id
    db.commit()

    turn_service.skip(db, session, compute_turn(db, "AAAA"))
    db.commit()

    turn = compute_turn(db, "AAAA")
    assert session.bumped_item_id is None
    assert turn.item.id == spencers.id


# ---------------------------------------------------------------------------
# Add performer, joining, remove and undo
# ---------------------------------------------------------------------------


def test_insert_at_the_pointer_holds_on_the_next_lap(db):
    session = _make_session(db)
    _make_song(db)
    spencer, dan, patrick, sarah = _people(db, "Spencer", "Dan", "Patrick", "Sarah")
    for p in (spencer, dan, patrick, sarah):
        _add_item(db, session, p)
        _add_item(db, session, p)
    session.turn_performer_id = patrick.id
    db.commit()

    jess = resolve_or_create_performer(db, "AAAA", "Jess")
    turn_service.insert_at_turn(db, session, jess)
    db.commit()
    assert _holder(db).id == jess.id
    _add_item(db, session, jess)
    _add_item(db, session, jess)

    order = ["Jess", "Patrick", "Sarah", "Spencer", "Dan"]
    assert _singers(db, session, 10) == order + order


def test_insert_keeps_seats_of_removed_people_in_place(db):
    """Inactive rows are renumbered too, so an undo lands in the right spot."""
    session = _make_session(db)
    spencer, dan, patrick = _people(db, "Spencer", "Dan", "Patrick")
    turn_service.remove(db, session, patrick)
    db.commit()

    jess = resolve_or_create_performer(db, "AAAA", "Jess")
    session.turn_performer_id = dan.id
    turn_service.insert_at_turn(db, session, jess)
    db.commit()

    assert [spencer.seat, jess.seat, dan.seat, patrick.seat] == [0, 1, 2, 3]


def test_phone_join_mid_lap_sings_before_the_wrap(db):
    session = _make_session(db)
    _make_song(db)
    spencer, dan, sarah = _people(db, "Spencer", "Dan", "Sarah")
    for p in (spencer, dan, sarah):
        _add_item(db, session, p)
    assert _singers(db, session, 1) == ["Spencer"]

    (jess,) = _people(db, "Jess")
    _add_item(db, session, jess)

    assert _singers(db, session, 3) == ["Dan", "Sarah", "Jess"]


def test_remove_then_undo_restores_seat_and_pointer(db):
    session = _make_session(db)
    spencer, dan, sarah = _people(db, "Spencer", "Dan", "Sarah")
    session.turn_performer_id = dan.id
    db.commit()

    turn_service.remove(db, session, dan)
    db.commit()
    holder_after_remove = _holder(db)
    assert holder_after_remove.id == sarah.id

    turn_service.restore(session, dan, point_back=True)
    db.commit()

    assert dan.is_active and dan.seat == 1
    assert _holder(db).id == dan.id


def test_remove_hides_their_songs_and_drops_their_bump(db):
    session = _make_session(db)
    _make_song(db)
    spencer, dan = _people(db, "Spencer", "Dan")
    spencers = _add_item(db, session, spencer)
    dans = _add_item(db, session, dan)
    session.bumped_item_id = dans.id
    db.commit()

    turn_service.remove(db, session, dan)
    db.commit()

    assert session.bumped_item_id is None
    assert [i.id for i in get_ordered_queue_items(db, "AAAA")] == [spencers.id]
    turn_service.restore(session, dan, point_back=False)
    db.commit()
    assert dans.id in [i.id for i in get_ordered_queue_items(db, "AAAA")]


def test_removing_the_last_person_leaves_the_floor_open(db):
    session = _make_session(db)
    (spencer,) = _people(db, "Spencer")

    turn_service.remove(db, session, spencer)
    db.commit()

    assert compute_turn(db, "AAAA").kind == KIND_OPEN
    assert session.turn_performer_id is None


def test_rejoining_by_name_goes_to_the_end_of_the_circle(db):
    session = _make_session(db)
    spencer, dan, sarah = _people(db, "Spencer", "Dan", "Sarah")
    dan.turns_borrowed = 1
    turn_service.remove(db, session, dan)
    db.commit()

    resolve_or_create_performer(db, "AAAA", "dan")
    db.commit()

    assert dan.is_active
    assert dan.seat == 3
    assert dan.turns_borrowed == 0


# ---------------------------------------------------------------------------
# Append mode
# ---------------------------------------------------------------------------


def test_append_mode_has_no_circle_and_no_empty_seat(db):
    _make_session(db, mode="append")
    _people(db, "Sarah")

    turn = compute_turn(db, "AAAA")
    assert turn.kind == KIND_OPEN
    assert turn.circle == []


def test_append_mode_plays_touch_no_rotation_state(db):
    session = _make_session(db, mode="append")
    _make_song(db)
    spencer, dan = _people(db, "Spencer", "Dan")
    _add_item(db, session, spencer, position=1)
    dans = _add_item(db, session, dan, position=2)

    _play(db, session, dans)

    assert session.turn_performer_id is None
    assert dan.turns_borrowed == 0


# ---------------------------------------------------------------------------
# The endpoints, including the race
# ---------------------------------------------------------------------------


def test_skip_endpoint_moves_the_turn(db, client):
    _make_session(db)
    spencer, dan = _people(db, "Spencer", "Dan")

    response = client.post(
        "/api/sessions/AAAA/turn/skip", json={"expected_performer_id": spencer.id}
    )
    assert response.status_code == 200
    assert response.json()["id"] == spencer.id

    db.expire_all()
    assert _holder(db).id == dan.id


def test_turn_endpoints_answer_409_when_the_turn_has_moved_on(db, client):
    _make_session(db)
    spencer, dan = _people(db, "Spencer", "Dan")

    for path, body in [
        ("/api/sessions/AAAA/turn/skip", {"expected_performer_id": dan.id}),
        (
            "/api/sessions/AAAA/turn/insert",
            {"expected_performer_id": dan.id, "name": "Jess"},
        ),
        (
            f"/api/sessions/AAAA/performers/{dan.id}/remove",
            {"expected_performer_id": dan.id},
        ),
    ]:
        assert client.post(path, json=body).status_code == 409, path

    db.expire_all()
    assert _holder(db).id == spencer.id
    assert db.query(SessionPerformer).filter_by(normalized_name="jess").first() is None


def test_insert_endpoint_seats_a_new_name_at_the_turn(db, client):
    _make_session(db)
    spencer, dan = _people(db, "Spencer", "Dan")

    response = client.post(
        "/api/sessions/AAAA/turn/insert",
        json={"expected_performer_id": spencer.id, "name": "Jess"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Jess"

    db.expire_all()
    circle = serialize_turn(compute_turn(db, "AAAA"))["circle"]
    assert [p["name"] for p in circle] == ["Jess", "Spencer", "Dan"]


def test_insert_endpoint_rejects_someone_already_in_the_circle(db, client):
    _make_session(db)
    spencer, dan = _people(db, "Spencer", "Dan")

    response = client.post(
        "/api/sessions/AAAA/turn/insert",
        json={"expected_performer_id": spencer.id, "name": " dan "},
    )
    assert response.status_code == 400

    db.expire_all()
    assert _holder(db).id == spencer.id


def test_insert_endpoint_brings_a_removed_person_back_at_the_turn(db, client):
    session = _make_session(db)
    spencer, dan, sarah = _people(db, "Spencer", "Dan", "Sarah")
    turn_service.remove(db, session, spencer)
    db.commit()

    response = client.post(
        "/api/sessions/AAAA/turn/insert",
        json={"expected_performer_id": dan.id, "name": "Spencer"},
    )
    assert response.status_code == 201

    db.expire_all()
    circle = serialize_turn(compute_turn(db, "AAAA"))["circle"]
    assert [p["name"] for p in circle] == ["Spencer", "Dan", "Sarah"]


def test_remove_then_restore_endpoints_round_trip(db, client):
    _make_session(db)
    spencer, dan = _people(db, "Spencer", "Dan")

    removed = client.post(
        f"/api/sessions/AAAA/performers/{spencer.id}/remove",
        json={"expected_performer_id": spencer.id},
    )
    assert removed.status_code == 200
    assert removed.json()["is_active"] is False
    assert removed.json()["holder_id"] == dan.id

    restored = client.post(
        f"/api/sessions/AAAA/performers/{spencer.id}/restore",
        json={"expected_holder_id": removed.json()["holder_id"]},
    )
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True

    db.expire_all()
    assert _holder(db).id == spencer.id


def test_restore_after_the_turn_moved_does_not_steal_it(db, client):
    session = _make_session(db)
    _make_song(db)
    spencer, dan, sarah = _people(db, "Spencer", "Dan", "Sarah")
    _add_item(db, session, dan)

    removed = client.post(
        f"/api/sessions/AAAA/performers/{spencer.id}/remove",
        json={"expected_performer_id": spencer.id},
    ).json()
    assert removed["holder_id"] == dan.id

    db.expire_all()
    session = db.query(KaraokeSession).filter_by(session_id="AAAA").one()
    _play_next(db, session)  # Dan sings; the turn moves to Sarah.

    client.post(
        f"/api/sessions/AAAA/performers/{spencer.id}/restore",
        json={"expected_holder_id": removed["holder_id"]},
    )

    db.expire_all()
    assert db.get(SessionPerformer, spencer.id).is_active is True
    assert _holder(db).id == sarah.id


def test_turn_endpoints_require_rotation_mode(db, client):
    _make_session(db, mode="append")
    (spencer,) = _people(db, "Spencer")

    response = client.post("/api/sessions/AAAA/turn/skip", json={})
    assert response.status_code == 400


def test_play_endpoint_records_the_turn(client, db):
    """The play endpoint mutates the session row `require_session_owner`
    resolved - this asserts that write actually lands, rather than being made
    on a second Session and dropped."""
    session = _make_session(db)
    _make_song(db)
    spencer, dan = _people(db, "Spencer", "Dan")
    spencers = _add_item(db, session, spencer)

    response = client.post(f"/api/karaoke-queue/{spencers.id}/play?session_code=AAAA")
    assert response.status_code == 200

    db.expire_all()
    session = db.query(KaraokeSession).filter_by(session_id="AAAA").one()
    assert session.turn_performer_id == dan.id
