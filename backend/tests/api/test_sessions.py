"""
REST tests for /api/sessions.

Beyond creating and joining, the lifecycle rule under test is that a session is *retired*,
never deleted: ending one - or letting the host's WebSocket grace period expire -
deactivates the row and its devices while the queue survives, and a host can then start
a fresh session with a new code.
"""

import uuid
from datetime import timedelta

from tests.api.conftest import _get_mock_user

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
from app.utils.clock import utc_now

HOST_USER_ID = 1


def _make_session(db, session_id="AAAA", host_user_id=HOST_USER_ID, is_active=True):
    """Insert a session with one host device and one queue item."""
    session = KaraokeSession(
        session_id=session_id,
        display_code=session_id,
        host_device_id=f"rest_{session_id.lower()}",
        host_user_id=host_user_id,
        expires_at=utc_now() + timedelta(hours=8),
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


def _create_session(client, device_type="stage", display_name=None):
    payload = {"device_type": device_type}
    if display_name:
        payload["display_name"] = display_name
    resp = client.post("/api/sessions", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# POST /  (create)
# ---------------------------------------------------------------------------


def test_create_session_returns_201(client):
    resp = client.post("/api/sessions", json={"device_type": "stage"})
    assert resp.status_code == 201
    data = resp.json()
    assert "session_id" in data
    assert "display_code" in data
    assert data["is_host"] is True
    assert data["is_active"] is True


def test_create_session_with_display_name(client):
    resp = client.post(
        "/api/sessions",
        json={"device_type": "stage", "display_name": "Test Host"},
    )
    assert resp.status_code == 201


def test_create_session_invalid_device_type(client):
    resp = client.post("/api/sessions", json={"device_type": "invalid_type"})
    assert resp.status_code == 400


def test_create_session_device_id_returned(client):
    data = _create_session(client)
    assert "device_id" in data
    assert data["device_id"].startswith("rest_")


def test_create_session_records_owning_user(client, db):
    """
    POST /api/sessions must persist host_user_id.

    Without it, host authority on the WebSocket - which derives from host_user_id - can
    never be granted for sessions created through this path.
    """
    session_id = _create_session(client)["session_id"]

    session = (
        db.query(KaraokeSession).filter(KaraokeSession.session_id == session_id).one()
    )
    assert session.host_user_id == HOST_USER_ID


# ---------------------------------------------------------------------------
# POST /join-by-code
# ---------------------------------------------------------------------------


def test_join_by_code_success(client):
    session = _create_session(client)
    code = session["display_code"]

    resp = client.post(
        "/api/sessions/join-by-code",
        json={"code": code, "device_type": "performer"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session["session_id"]
    assert data["is_host"] is False


def test_join_by_code_not_found(client):
    resp = client.post(
        "/api/sessions/join-by-code",
        json={"code": "XXXX", "device_type": "performer"},
    )
    assert resp.status_code == 404


def test_join_by_code_invalid_device_type(client):
    session = _create_session(client)
    resp = client.post(
        "/api/sessions/join-by-code",
        json={"code": session["display_code"], "device_type": "bad_type"},
    )
    assert resp.status_code == 400


def test_join_by_code_lowercased_code_works(client):
    session = _create_session(client)
    code = session["display_code"].lower()
    resp = client.post(
        "/api/sessions/join-by-code",
        json={"code": code, "device_type": "performer"},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /join-by-id
# ---------------------------------------------------------------------------


def test_join_by_id_success(client):
    session = _create_session(client)
    resp = client.post(
        "/api/sessions/join-by-id",
        json={"session_id": session["session_id"], "device_type": "performer"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session["session_id"]


def test_join_by_id_not_found(client):
    resp = client.post(
        "/api/sessions/join-by-id",
        json={"session_id": str(uuid.uuid4()), "device_type": "performer"},
    )
    assert resp.status_code == 404


def test_join_by_id_invalid_device_type(client):
    session = _create_session(client)
    resp = client.post(
        "/api/sessions/join-by-id",
        json={"session_id": session["session_id"], "device_type": "bad_type"},
    )
    assert resp.status_code == 400


def test_join_by_id_already_joined_returns_409(client):
    """Joining twice from the same IP should return 409 conflict."""
    session = _create_session(client)
    payload = {"session_id": session["session_id"], "device_type": "performer"}
    # First join
    resp1 = client.post("/api/sessions/join-by-id", json=payload)
    assert resp1.status_code == 200
    # Second join from same IP (testclient uses 'testclient' host)
    resp2 = client.post("/api/sessions/join-by-id", json=payload)
    assert resp2.status_code == 409


# ---------------------------------------------------------------------------
# GET /{session_id}/info and /{session_id}/validate
# ---------------------------------------------------------------------------


def test_get_session_info_success(client):
    session = _create_session(client)
    resp = client.get(f"/api/sessions/{session['session_id']}/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session["session_id"]


def test_get_session_info_with_device_id(client):
    session = _create_session(client)
    device_id = session["device_id"]
    resp = client.get(
        f"/api/sessions/{session['session_id']}/info?device_id={device_id}"
    )
    assert resp.status_code == 200


def test_get_session_info_not_found(client):
    resp = client.get(f"/api/sessions/{uuid.uuid4()}/info")
    assert resp.status_code == 404


def test_validate_session_valid(client):
    session = _create_session(client)
    resp = client.get(f"/api/sessions/{session['session_id']}/validate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["session_id"] == session["session_id"]


def test_validate_session_not_found(client):
    resp = client.get(f"/api/sessions/{uuid.uuid4()}/validate")
    assert resp.status_code == 404


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


def test_leave_session_requires_a_membership_credential(client):
    session = _create_session(client)
    resp = client.post(f"/api/sessions/{session['session_id']}/leave")
    # Leaving identifies the device by its X-Session-ID / X-Device-ID credential; without
    # one there is no device to leave.
    assert resp.status_code == 422


def test_leave_session_rejects_an_unknown_device(client):
    session = _create_session(client)
    resp = client.post(
        f"/api/sessions/{session['session_id']}/leave",
        headers=_member_headers(session["session_id"], "rest_not_a_real_device"),
    )
    assert resp.status_code == 403


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
# GET /my and POST /my
# ---------------------------------------------------------------------------


def test_get_my_session_returns_null_when_none(client):
    resp = client.get("/api/sessions/my")
    assert resp.status_code == 200
    assert resp.json() is None


def test_post_my_without_a_device_id_returns_the_live_session(client):
    """A second stage without a stored device id joins the live session, not a new one."""
    payload = {"device_type": "stage", "display_name": "Host"}
    first = client.post("/api/sessions/my", json=payload)
    assert first.status_code == 201

    second = client.post("/api/sessions/my", json=payload)
    assert second.status_code == 201

    assert second.json()["session_id"] == first.json()["session_id"]


def test_post_my_ignores_stale_active_sessions(client, db):
    """
    A stale expired-but-active row must not shadow the host's live session.

    Regression: the lookup had no ORDER BY and checked expiry only after the query, so an
    unordered .first() could return an expired row, fail the expiry check, and mint a
    brand new session - orphaning a live one that still had performers in it. This is what
    produced two simultaneously active production sessions (MEBD and HPVT) for one host.
    """
    payload = {"device_type": "stage", "display_name": "Host"}

    live_session_id = client.post("/api/sessions/my", json=payload).json()["session_id"]

    # An older, already-expired session still flagged active for the same host.
    db.add(
        KaraokeSession(
            session_id="STLE",
            display_code="STLE",
            host_device_id="rest_stale000000",
            host_user_id=HOST_USER_ID,
            is_active=True,
            created_at=utc_now() - timedelta(days=3),
            expires_at=utc_now() - timedelta(days=2),
        )
    )
    db.commit()

    resp = client.post("/api/sessions/my", json=payload)
    assert resp.status_code == 201
    assert resp.json()["session_id"] == live_session_id

    # The stale row should also have been reconciled rather than left active.
    stale = db.query(KaraokeSession).filter(KaraokeSession.session_id == "STLE").one()
    db.refresh(stale)
    assert stale.is_active is False


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
    old.created_at = utc_now() - timedelta(days=30)
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
