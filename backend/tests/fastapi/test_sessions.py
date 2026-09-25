"""
REST tests for the session lifecycle.

The behaviour under test is that a session is *retired*, never deleted: ending one - or
letting the host's WebSocket grace period expire - deactivates the row and its devices
while the queue survives, and a host can then start a fresh session with a new code.
"""

from datetime import datetime, timedelta

import pytest
from app.api.dependencies import get_current_user
from app.api.sessions import purge_stale_sessions
from app.db.models import (
    HostSettings,
    KaraokeQueueItem,
    KaraokeSession,
    SessionDevice,
    SessionPerformer,
)
from app.services.session_service import deactivate_session
from tests.fastapi.conftest import _get_mock_user, _TestingSessionLocal

HOST_USER_ID = 1


@pytest.fixture
def db():
    session = _TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_session(db, session_id="AAAA", host_user_id=HOST_USER_ID, is_active=True):
    """Insert a session with one host device and one queue item."""
    session = KaraokeSession(
        session_id=session_id,
        display_code=session_id,
        host_device_id=f"rest_{session_id.lower()}",
        host_user_id=host_user_id,
        expires_at=datetime.utcnow() + timedelta(hours=8),
        is_active=is_active,
    )
    db.add(session)
    db.add(
        SessionDevice(
            session_id=session_id,
            device_id=f"rest_{session_id.lower()}",
            device_type="stage",
        )
    )
    db.add(
        KaraokeQueueItem(
            singer_name="Spencer",
            song_id="test-song-123",
            position=1,
            session_id=session_id,
        )
    )
    db.commit()
    return session


def _member_headers(session_id, device_id):
    return {"X-Session-ID": session_id, "X-Device-ID": device_id}


# ---------------------------------------------------------------------------
# POST /{session_id}/leave
# ---------------------------------------------------------------------------


def test_leave_deactivates_the_calling_device(client, db):
    """Regression: /leave used to match devices by request IP, so it always 404'd."""
    _make_session(db, "AAAA")
    db.add(
        SessionDevice(
            session_id="AAAA", device_id="rest_phone", device_type="performer"
        )
    )
    db.commit()

    response = client.post(
        "/api/sessions/AAAA/leave", headers=_member_headers("AAAA", "rest_phone")
    )

    assert response.status_code == 200

    phone = (
        db.query(SessionDevice).filter(SessionDevice.device_id == "rest_phone").one()
    )
    stage = db.query(SessionDevice).filter(SessionDevice.device_id == "rest_aaaa").one()
    db.refresh(phone)
    db.refresh(stage)
    assert phone.is_active is False
    # A device leaving must not take the session or the other devices with it.
    assert stage.is_active is True
    assert db.query(KaraokeSession).one().is_active is True


def test_leave_rejects_a_device_from_another_session(client, db):
    _make_session(db, "AAAA")
    _make_session(db, "BBBB")

    response = client.post(
        "/api/sessions/AAAA/leave", headers=_member_headers("BBBB", "rest_bbbb")
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /{session_id}
# ---------------------------------------------------------------------------


def test_delete_retires_the_session_but_keeps_the_queue(client, db):
    _make_session(db, "AAAA")

    response = client.delete("/api/sessions/AAAA")

    assert response.status_code == 200

    session = db.query(KaraokeSession).one()
    db.refresh(session)
    assert session.is_active is False
    assert all(not d.is_active for d in db.query(SessionDevice).all())
    assert db.query(KaraokeQueueItem).count() == 1


def test_delete_rejects_a_host_who_does_not_own_the_session(client, db, fastapi_app):
    _make_session(db, "AAAA", host_user_id=HOST_USER_ID)

    other_host = _get_mock_user()
    other_host.id = 99
    fastapi_app.dependency_overrides[get_current_user] = lambda: other_host
    try:
        response = client.delete("/api/sessions/AAAA")
    finally:
        fastapi_app.dependency_overrides[get_current_user] = _get_mock_user

    assert response.status_code == 403

    session = db.query(KaraokeSession).one()
    db.refresh(session)
    assert session.is_active is True


def test_delete_404s_for_an_unknown_session(client):
    assert client.delete("/api/sessions/ZZZZ").status_code == 404


# ---------------------------------------------------------------------------
# POST /my
# ---------------------------------------------------------------------------


def test_post_my_reuses_the_session_and_the_device_row(client, db):
    first = client.post("/api/sessions/my", json={"device_type": "stage"})
    assert first.status_code == 201
    device_id = first.json()["device_id"]

    second = client.post(
        "/api/sessions/my", json={"device_type": "stage", "device_id": device_id}
    )

    assert second.status_code == 201
    assert second.json()["session_id"] == first.json()["session_id"]
    assert second.json()["device_id"] == device_id
    assert second.json()["device_count"] == 1
    assert db.query(SessionDevice).count() == 1


def test_post_my_after_delete_yields_a_new_code(client):
    """The acceptance test: a host can end the night and start a fresh session."""
    first = client.post("/api/sessions/my", json={"device_type": "stage"}).json()

    assert client.delete(f"/api/sessions/{first['session_id']}").status_code == 200

    second = client.post("/api/sessions/my", json={"device_type": "stage"}).json()

    assert second["session_id"] != first["session_id"]
    assert second["display_code"] != first["display_code"]
    assert second["is_active"] is True


# ---------------------------------------------------------------------------
# POST /my - setup from the create-session screen
# ---------------------------------------------------------------------------


def _performers(db, session_id):
    return (
        db.query(SessionPerformer)
        .filter(SessionPerformer.session_id == session_id)
        .all()
    )


def test_post_my_seeds_the_roster_with_performer_names(client, db):
    response = client.post(
        "/api/sessions/my",
        json={"device_type": "stage", "performer_names": ["Dan", "Sarah"]},
    )

    assert response.status_code == 201
    performers = {p.name: p for p in _performers(db, response.json()["session_id"])}
    # The host's own display_name already took a seat, so don't assert 0 and 1.
    assert {"Dan", "Sarah"} <= set(performers)
    assert performers["Dan"].seat < performers["Sarah"].seat


def test_post_my_skips_blank_performer_names(client, db):
    response = client.post(
        "/api/sessions/my",
        json={"device_type": "stage", "performer_names": ["", "   ", "Dan"]},
    )

    assert response.status_code == 201
    names = [p.name for p in _performers(db, response.json()["session_id"])]
    assert "Dan" in names
    assert all(name.strip() for name in names)


def test_post_my_seats_the_host_by_default(client, db):
    response = client.post("/api/sessions/my", json={"device_type": "stage"})

    assert response.status_code == 201
    performers = _performers(db, response.json()["session_id"])
    assert [p.device_id for p in performers] == [response.json()["device_id"]]


def test_post_my_can_leave_the_host_off_the_roster(client, db):
    response = client.post(
        "/api/sessions/my",
        json={
            "device_type": "stage",
            "include_host_in_roster": False,
            "performer_names": ["Dan"],
        },
    )

    assert response.status_code == 201
    performers = _performers(db, response.json()["session_id"])
    # Only the pre-listed name took a seat; the host is running the night.
    assert [p.name for p in performers] == ["Dan"]
    assert performers[0].seat == 0


def test_post_my_duration_hours_overrides_the_host_default(client, db):
    db.add(HostSettings(user_id=HOST_USER_ID, session_duration_hours=8))
    db.commit()

    response = client.post(
        "/api/sessions/my", json={"device_type": "stage", "duration_hours": 2}
    )

    assert response.status_code == 201
    session = (
        db.query(KaraokeSession)
        .filter(KaraokeSession.session_id == response.json()["session_id"])
        .one()
    )
    span = (session.expires_at - session.created_at).total_seconds()
    assert abs(span - 2 * 3600) < 60
    # The override is for tonight only - the stored default is untouched.
    settings = db.query(HostSettings).filter(HostSettings.user_id == HOST_USER_ID).one()
    assert settings.session_duration_hours == 8


def test_post_my_queue_order_mode_override(client, db):
    response = client.post(
        "/api/sessions/my", json={"device_type": "stage", "queue_order_mode": "append"}
    )

    assert response.status_code == 201
    assert response.json()["queue_order_mode"] == "append"
    session = (
        db.query(KaraokeSession)
        .filter(KaraokeSession.session_id == response.json()["session_id"])
        .one()
    )
    assert session.queue_order_mode == "append"


def test_post_my_defaults_to_rotation_without_an_override(client):
    """Guards the column default still applying to a no-setup call."""
    response = client.post("/api/sessions/my", json={"device_type": "stage"})

    assert response.status_code == 201
    assert response.json()["queue_order_mode"] == "rotation"


def test_post_my_ignores_setup_fields_for_an_existing_session(client, db):
    first = client.post("/api/sessions/my", json={"device_type": "stage"}).json()
    session = (
        db.query(KaraokeSession)
        .filter(KaraokeSession.session_id == first["session_id"])
        .one()
    )
    expires_at, roster_size = session.expires_at, len(
        _performers(db, session.session_id)
    )

    second = client.post(
        "/api/sessions/my",
        json={
            "device_type": "stage",
            "device_id": first["device_id"],
            "performer_names": ["Dan", "Sarah"],
            "duration_hours": 99,
            "queue_order_mode": "append",
        },
    )

    assert second.status_code == 201
    assert second.json()["session_id"] == first["session_id"]
    db.refresh(session)
    # Starting a session does not reshape one that is already live.
    assert session.queue_order_mode == "rotation"
    assert session.expires_at == expires_at
    assert len(_performers(db, session.session_id)) == roster_size


def test_post_my_resume_does_not_reseat_a_host_who_opted_out(client, db):
    first = client.post(
        "/api/sessions/my",
        json={"device_type": "stage", "include_host_in_roster": False},
    ).json()

    # A second device (or a remount without a stored device id) resumes the session.
    second = client.post("/api/sessions/my", json={"device_type": "stage"})

    assert second.status_code == 201
    assert second.json()["session_id"] == first["session_id"]
    assert _performers(db, first["session_id"]) == []


def test_post_my_reject_409s_with_the_live_session(client, db):
    first = client.post("/api/sessions/my", json={"device_type": "stage"}).json()

    response = client.post(
        "/api/sessions/my",
        json={
            "device_type": "stage",
            "on_existing": "reject",
            "performer_names": ["Dan"],
        },
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["session_id"] == first["session_id"]
    assert detail["display_code"] == first["display_code"]
    # Nothing was written to the live session.
    assert "Dan" not in [p.name for p in _performers(db, first["session_id"])]


def test_post_my_reject_creates_when_no_session_is_live(client, db):
    response = client.post(
        "/api/sessions/my",
        json={
            "device_type": "stage",
            "on_existing": "reject",
            "performer_names": ["Dan"],
        },
    )

    assert response.status_code == 201
    assert "Dan" in [p.name for p in _performers(db, response.json()["session_id"])]


def test_post_my_replace_retires_the_live_session_and_applies_setup(client, db):
    first = client.post("/api/sessions/my", json={"device_type": "stage"}).json()

    response = client.post(
        "/api/sessions/my",
        json={
            "device_type": "stage",
            "on_existing": "replace",
            "include_host_in_roster": False,
            "performer_names": ["Dan", "Sarah", "Priya", "Tom"],
            "queue_order_mode": "append",
        },
    )

    assert response.status_code == 201
    new_id = response.json()["session_id"]
    assert new_id != first["session_id"]
    assert response.json()["queue_order_mode"] == "append"
    seated = sorted(_performers(db, new_id), key=lambda p: p.seat)
    assert [p.name for p in seated] == ["Dan", "Sarah", "Priya", "Tom"]

    old = (
        db.query(KaraokeSession)
        .filter(KaraokeSession.session_id == first["session_id"])
        .one()
    )
    db.refresh(old)
    assert old.is_active is False


# ---------------------------------------------------------------------------
# Retention helpers
# ---------------------------------------------------------------------------


def test_purge_removes_long_dead_sessions_only(db):
    _make_session(db, "AAAA", is_active=False)
    _make_session(db, "BBBB", is_active=False)
    _make_session(db, "CCCC", is_active=True)

    old = db.query(KaraokeSession).filter(KaraokeSession.session_id == "AAAA").one()
    old.created_at = datetime.utcnow() - timedelta(days=30)
    db.commit()

    assert purge_stale_sessions(db, older_than_days=7) == 1

    remaining = {s.session_id for s in db.query(KaraokeSession).all()}
    assert remaining == {"BBBB", "CCCC"}
    # The purged session took its queue with it; the retained ones kept theirs.
    assert db.query(KaraokeQueueItem).count() == 2


def test_deactivate_session_keeps_the_queue(db):
    """The WebSocket host-disconnect grace period ends here; it used to db.delete()."""
    _make_session(db, "AAAA")

    assert deactivate_session(db, "AAAA") is True

    session = db.query(KaraokeSession).one()
    db.refresh(session)
    assert session.is_active is False
    assert all(not d.is_active for d in db.query(SessionDevice).all())
    assert db.query(KaraokeQueueItem).count() == 1


def test_deactivate_session_is_a_noop_for_an_unknown_session(db):
    assert deactivate_session(db, "ZZZZ") is False
