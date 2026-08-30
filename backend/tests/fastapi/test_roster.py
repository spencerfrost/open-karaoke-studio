"""
Tests for the session roster (unit 3a): resolve_or_create_performer and the
/api/sessions/{id}/performers endpoints.
"""

from datetime import datetime, timedelta

import pytest
from app.db.models import KaraokeSession, SessionPerformer
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


# ---------------------------------------------------------------------------
# resolve_or_create_performer
# ---------------------------------------------------------------------------


def test_resolve_or_create_performer_creates_a_new_row(db):
    _make_session(db, "AAAA")

    performer = resolve_or_create_performer(db, "AAAA", "Spencer")
    db.commit()

    assert performer.name == "Spencer"
    assert performer.normalized_name == "spencer"
    assert performer.seat == 0
    assert db.query(SessionPerformer).count() == 1


def test_resolve_or_create_performer_dedupes_case_and_whitespace(db):
    _make_session(db, "AAAA")

    first = resolve_or_create_performer(db, "AAAA", "Spencer")
    db.commit()
    second = resolve_or_create_performer(db, "AAAA", "  spencer  ")
    db.commit()

    assert first.id == second.id
    assert db.query(SessionPerformer).count() == 1


def test_resolve_or_create_performer_assigns_sequential_seats(db):
    _make_session(db, "AAAA")

    first = resolve_or_create_performer(db, "AAAA", "Spencer")
    db.commit()
    second = resolve_or_create_performer(db, "AAAA", "Dan")
    db.commit()

    assert first.seat == 0
    assert second.seat == 1


def test_resolve_or_create_performer_scopes_seats_per_session(db):
    _make_session(db, "AAAA")
    _make_session(db, "BBBB")

    resolve_or_create_performer(db, "AAAA", "Spencer")
    db.commit()
    other_session_first = resolve_or_create_performer(db, "BBBB", "Dan")
    db.commit()

    assert other_session_first.seat == 0


def test_resolve_or_create_performer_rejects_empty_name(db):
    _make_session(db, "AAAA")

    with pytest.raises(ValueError):
        resolve_or_create_performer(db, "AAAA", "   ")


def test_resolve_or_create_performer_links_a_device_only_once(db):
    """A device attaches to a fresh row; it never steals one from another device."""
    _make_session(db, "AAAA")

    performer = resolve_or_create_performer(db, "AAAA", "Spencer", device_id="phone-1")
    db.commit()
    same = resolve_or_create_performer(db, "AAAA", "Spencer", device_id="phone-2")
    db.commit()

    assert performer.id == same.id
    assert same.device_id == "phone-1"


# ---------------------------------------------------------------------------
# GET/POST /api/sessions/{id}/performers
# ---------------------------------------------------------------------------


def test_list_performers_returns_active_roster(client, db):
    _make_session(db, "AAAA")
    resolve_or_create_performer(db, "AAAA", "Spencer")
    resolve_or_create_performer(db, "AAAA", "Dan")
    db.commit()

    response = client.get("/api/sessions/AAAA/performers")

    assert response.status_code == 200
    names = {p["name"] for p in response.json()}
    assert names == {"Spencer", "Dan"}


def test_add_performer_creates_a_roster_entry(client, db):
    _make_session(db, "AAAA")

    response = client.post("/api/sessions/AAAA/performers", json={"name": "Sarah"})

    assert response.status_code == 201
    assert response.json()["name"] == "Sarah"
    assert response.json()["seat"] == 0
    assert db.query(SessionPerformer).filter_by(normalized_name="sarah").count() == 1


def test_add_performer_dedupes_against_an_existing_entry(client, db):
    _make_session(db, "AAAA")
    client.post("/api/sessions/AAAA/performers", json={"name": "Sarah"})

    response = client.post("/api/sessions/AAAA/performers", json={"name": "sarah"})

    assert response.status_code == 201
    assert db.query(SessionPerformer).count() == 1


def test_add_performer_404s_for_an_unknown_session(client):
    response = client.post("/api/sessions/ZZZZ/performers", json={"name": "Sarah"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Phone join populates the roster
# ---------------------------------------------------------------------------


def test_join_by_code_creates_a_roster_entry(client, db):
    _make_session(db, "AAAA")

    response = client.post(
        "/api/sessions/join-by-code",
        json={"code": "AAAA", "device_type": "performer", "display_name": "Sarah"},
    )

    assert response.status_code == 200
    performer = (
        db.query(SessionPerformer)
        .filter_by(session_id="AAAA", normalized_name="sarah")
        .one()
    )
    assert performer.device_id == response.json()["device_id"]


def test_join_by_code_without_a_name_creates_no_roster_entry(client, db):
    _make_session(db, "BBBB")

    response = client.post(
        "/api/sessions/join-by-code",
        json={"code": "BBBB", "device_type": "controller"},
    )

    assert response.status_code == 200
    assert db.query(SessionPerformer).filter_by(session_id="BBBB").count() == 0
