"""
Tests for unit 4: whose turn it is, and the three ways that changes.

The mechanism these guard is the one the handoff screen renders, so the cases
follow docs/plans/2026-08-29-handoff-screen.md's state table directly: a queued
turn, an empty seat, an open floor, the one-lap pass, the claim, and the 409
that makes two devices acting at once safe.
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
from app.services.queue_ordering import advance_to, compute_lap, enter_rotation
from app.services.roster_service import resolve_or_create_performer
from app.services.turn_service import (
    KIND_EMPTY_SEAT,
    KIND_OPEN,
    KIND_QUEUED,
    claim_turn,
    compute_turn,
    pass_turn,
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


def _add_item(db, session, performer, song_id, position=1):
    """Insert a queue item the way add_to_queue does."""
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


def _set_playing(db, session_id, item_id):
    db.add(SessionPlaybackState(session_id=session_id, current_queue_item_id=item_id))
    db.commit()


# ---------------------------------------------------------------------------
# compute_turn - the three kinds
# ---------------------------------------------------------------------------


def test_turn_is_the_head_of_the_queue(db):
    session = _make_session(db)
    _make_song(db)
    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    dan = resolve_or_create_performer(db, "AAAA", "Dan")
    db.commit()

    _add_item(db, session, spencer, "test-song")
    _add_item(db, session, dan, "test-song", position=2)

    turn = compute_turn(db, "AAAA")
    assert turn.kind == KIND_QUEUED
    assert turn.performer.id == spencer.id
    assert turn.item is not None


def test_currently_playing_item_is_not_the_turn(db):
    """The turn is what happens *next*, so the song on screen is excluded."""
    session = _make_session(db)
    _make_song(db)
    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    dan = resolve_or_create_performer(db, "AAAA", "Dan")
    db.commit()

    playing = _add_item(db, session, spencer, "test-song")
    dans_item = _add_item(db, session, dan, "test-song", position=2)
    _set_playing(db, "AAAA", playing.id)

    turn = compute_turn(db, "AAAA")
    assert turn.performer.id == dan.id
    assert turn.item.id == dans_item.id


def test_empty_queue_is_a_persons_turn_not_the_end_of_the_night(db):
    """The whole reframe: an empty queue is Sarah's turn with an empty slot."""
    _make_session(db)
    sarah = resolve_or_create_performer(db, "AAAA", "Sarah")
    db.commit()

    turn = compute_turn(db, "AAAA")
    assert turn.kind == KIND_EMPTY_SEAT
    assert turn.performer.id == sarah.id
    assert turn.item is None


def test_empty_roster_is_open(db):
    _make_session(db)
    turn = compute_turn(db, "AAAA")
    assert turn.kind == KIND_OPEN
    assert turn.performer is None
    assert turn.circle == []


def test_append_mode_has_no_circle_and_no_empty_seat(db):
    """Append mode has no rotation to ask, so an empty queue is just open."""
    _make_session(db, mode="append")
    resolve_or_create_performer(db, "AAAA", "Sarah")
    db.commit()

    turn = compute_turn(db, "AAAA")
    assert turn.kind == KIND_OPEN
    assert turn.circle == []


def test_circle_puts_the_person_who_just_sang_last(db):
    """No special case needed - advance_to already moved their laps_taken."""
    session = _make_session(db)
    _make_song(db)
    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    dan = resolve_or_create_performer(db, "AAAA", "Dan")
    db.commit()

    item = _add_item(db, session, spencer, "test-song")
    advance_to(session, item)
    db.commit()

    turn = compute_turn(db, "AAAA")
    assert [p.id for p in turn.circle] == [dan.id, spencer.id]


def test_solo_singer_comes_straight_back_round(db):
    session = _make_session(db)
    _make_song(db)
    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    db.commit()

    item = _add_item(db, session, spencer, "test-song")
    advance_to(session, item)
    db.delete(item)
    db.commit()

    turn = compute_turn(db, "AAAA")
    assert turn.kind == KIND_EMPTY_SEAT
    assert turn.performer.id == spencer.id


def test_serialize_falls_back_to_singer_name_for_pre_roster_rows(db):
    """Legacy rows have no performer_id; the screen still needs a name."""
    session = _make_session(db)
    _make_song(db)
    item = KaraokeQueueItem(
        singer_name="Ghost",
        song_id="test-song",
        session_id=session.session_id,
        position=1,
        lap=0,
    )
    db.add(item)
    db.commit()

    payload = serialize_turn(compute_turn(db, "AAAA"))
    assert payload["performerName"] == "Ghost"
    assert payload["performerId"] is None
    assert payload["itemId"] == item.id


# ---------------------------------------------------------------------------
# Passing - a full lap, never back to the front
# ---------------------------------------------------------------------------


def test_pass_moves_the_item_one_lap_forward_not_to_the_front(db):
    session = _make_session(db)
    _make_song(db)
    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    dan = resolve_or_create_performer(db, "AAAA", "Dan")
    db.commit()

    spencers = _add_item(db, session, spencer, "test-song")
    _add_item(db, session, dan, "test-song", position=2)
    assert spencers.lap == 0

    pass_turn(session, compute_turn(db, "AAAA"))
    db.commit()

    # One lap forward, so Dan sings next and Spencer follows - not immediately
    # re-offered, which an unchanged low lap would have done.
    assert spencers.lap == 1
    assert compute_turn(db, "AAAA").performer.id == dan.id


def test_pass_with_an_empty_seat_moves_laps_taken(db):
    """No item to rewrite, so the pass has to land on the performer."""
    _make_session(db)
    sarah = resolve_or_create_performer(db, "AAAA", "Sarah")
    dan = resolve_or_create_performer(db, "AAAA", "Dan")
    db.commit()

    assert compute_turn(db, "AAAA").performer.id == sarah.id

    session = db.query(KaraokeSession).filter_by(session_id="AAAA").one()
    pass_turn(session, compute_turn(db, "AAAA"))
    db.commit()

    assert sarah.laps_taken == 1
    assert compute_turn(db, "AAAA").performer.id == dan.id


def test_passing_never_takes_anyone_off_the_roster(db):
    """Nobody is rushed: a seat nobody stepped up for keeps coming round."""
    session = _make_session(db)
    sarah = resolve_or_create_performer(db, "AAAA", "Sarah")
    dan = resolve_or_create_performer(db, "AAAA", "Dan")
    db.commit()

    for _ in range(6):
        pass_turn(session, compute_turn(db, "AAAA"))
        db.commit()

    assert sarah.is_active is True
    assert dan.is_active is True
    assert compute_turn(db, "AAAA").kind == KIND_EMPTY_SEAT


def test_queueing_restores_a_seat_that_stepped_out(db):
    _make_session(db)
    sarah = resolve_or_create_performer(db, "AAAA", "Sarah")
    # What "Skip me for now" does - the only way a seat goes inactive.
    sarah.is_active = False
    db.commit()

    resolve_or_create_performer(db, "AAAA", "sarah")
    db.commit()

    assert sarah.is_active is True


# ---------------------------------------------------------------------------
# Claiming - "That's not me"
# ---------------------------------------------------------------------------


def test_claim_pulls_the_claimants_song_to_the_front(db):
    session = _make_session(db)
    _make_song(db)
    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    dan = resolve_or_create_performer(db, "AAAA", "Dan")
    db.commit()

    spencers = _add_item(db, session, spencer, "test-song")
    dans = _add_item(db, session, dan, "test-song", position=2)

    claim_turn(db, session, compute_turn(db, "AAAA"), dan)
    db.commit()

    turn = compute_turn(db, "AAAA")
    assert turn.performer.id == dan.id
    assert turn.item.id == dans.id
    # And Spencer is one lap out, not gone.
    assert spencers.lap == 1


def test_claim_without_a_song_still_takes_the_turn(db):
    session = _make_session(db)
    sarah = resolve_or_create_performer(db, "AAAA", "Sarah")
    dan = resolve_or_create_performer(db, "AAAA", "Dan")
    db.commit()
    assert compute_turn(db, "AAAA").performer.id == sarah.id

    claim_turn(db, session, compute_turn(db, "AAAA"), dan)
    db.commit()

    turn = compute_turn(db, "AAAA")
    assert turn.kind == KIND_EMPTY_SEAT
    assert turn.performer.id == dan.id


def test_claiming_your_own_turn_is_a_no_op(db):
    """Idempotent, so a race between two devices settles instead of double-passing."""
    session = _make_session(db)
    _make_song(db)
    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    db.commit()
    spencers = _add_item(db, session, spencer, "test-song")

    claim_turn(db, session, compute_turn(db, "AAAA"), spencer)
    db.commit()

    assert spencers.lap == 0
    assert compute_turn(db, "AAAA").performer.id == spencer.id


def test_claim_reactivates_someone_who_stepped_out(db):
    session = _make_session(db)
    sarah = resolve_or_create_performer(db, "AAAA", "Sarah")
    dan = resolve_or_create_performer(db, "AAAA", "Dan")
    dan.is_active = False
    db.commit()

    claim_turn(db, session, compute_turn(db, "AAAA"), dan)
    db.commit()

    assert dan.is_active is True
    assert compute_turn(db, "AAAA").performer.id == dan.id
    assert sarah.laps_taken == 1


# ---------------------------------------------------------------------------
# The endpoints, including the race
# ---------------------------------------------------------------------------


def test_claim_endpoint_accepts_a_new_name(db, client):
    """The picker's "Someone else…" creates a roster entry and takes the turn."""
    session = _make_session(db)
    _make_song(db)
    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    db.commit()
    _add_item(db, session, spencer, "test-song")

    response = client.post(
        "/api/sessions/AAAA/turn/claim",
        json={"expected_performer_id": spencer.id, "name": "Sarah"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Sarah"

    db.expire_all()
    sarah = (
        db.query(SessionPerformer)
        .filter_by(session_id="AAAA", normalized_name="sarah")
        .one()
    )
    assert compute_turn(db, "AAAA").performer.id == sarah.id


def test_deactivate_endpoint_steps_someone_out_and_passes_their_turn(db, client):
    session = _make_session(db)
    _make_song(db)
    spencer = resolve_or_create_performer(db, "AAAA", "Spencer")
    dan = resolve_or_create_performer(db, "AAAA", "Dan")
    db.commit()
    spencers = _add_item(db, session, spencer, "test-song")

    response = client.post(f"/api/sessions/AAAA/performers/{spencer.id}/deactivate")
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    db.expire_all()
    assert spencers.lap == 1
    assert compute_turn(db, "AAAA").performer.id == dan.id
