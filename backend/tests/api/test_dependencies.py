"""Tests for the auth and database dependencies in app/api/dependencies.py.

The endpoint tests override these, so they run here directly, on real users,
tokens and session devices.
"""

from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app.api.dependencies import (
    get_current_user,
    get_db,
    require_admin,
    require_host,
    require_host_or_session_member,
    require_session_member,
)
from app.db.models import KaraokeSession, SessionDevice, User
from app.services.auth_service import ALGORITHM, _get_secret_key, create_access_token
from app.utils.clock import utc_now


def _bearer(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _user(db, username="sam", **roles):
    user = User(username=username, **roles)
    db.add(user)
    db.commit()
    return user


def _session_with_device(db, session_id="ABCD", device_id="phone", expired=False):
    db.add(
        KaraokeSession(
            session_id=session_id,
            display_code=session_id,
            host_device_id="stage",
            expires_at=utc_now() + timedelta(hours=-1 if expired else 8),
        )
    )
    db.add(
        SessionDevice(
            session_id=session_id, device_id=device_id, device_type="performer"
        )
    )
    db.commit()


def _status(exc_info):
    return exc_info.value.status_code


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_valid_token_returns_the_user(self, db):
        user = _user(db)

        result = await get_current_user(_bearer(create_access_token(user)), db)

        assert result.id == user.id

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "token",
        [
            "not-a-jwt",
            pytest.param("expired", id="expired"),
            pytest.param("no-sub", id="no-sub"),
            pytest.param("deleted-user", id="deleted-user"),
        ],
    )
    async def test_bad_tokens_are_401(self, db, token):
        if token == "expired":
            token = create_access_token(_user(db), expires_minutes=-1)
        elif token == "no-sub":
            token = jwt.encode({"username": "sam"}, _get_secret_key(), ALGORITHM)
        elif token == "deleted-user":
            token = create_access_token(User(id=999, username="gone"))

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(_bearer(token), db)

        assert _status(exc_info) == 401
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


class TestRoleChecks:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "roles", [{"is_host": True}, {"is_admin": True}], ids=["host", "admin"]
    )
    async def test_require_host_accepts_hosts_and_admins(self, roles):
        user = User(username="sam", **roles)

        assert await require_host(user) is user

    @pytest.mark.asyncio
    async def test_require_host_rejects_guests(self):
        with pytest.raises(HTTPException) as exc_info:
            await require_host(User(username="sam", is_host=False, is_admin=False))

        assert _status(exc_info) == 403

    @pytest.mark.asyncio
    async def test_require_admin_accepts_admins(self):
        user = User(username="sam", is_admin=True)

        assert await require_admin(user) is user

    @pytest.mark.asyncio
    async def test_require_admin_rejects_hosts(self):
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(User(username="sam", is_host=True, is_admin=False))

        assert _status(exc_info) == 403


class TestRequireSessionMember:
    @pytest.mark.asyncio
    async def test_active_device_is_returned(self, db):
        _session_with_device(db)

        device = await require_session_member("ABCD", "phone", db)

        assert device.device_id == "phone"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "session_id, device_id, expired",
        [
            ("ABCD", "someone-else", False),
            ("WXYZ", "phone", False),
            ("ABCD", "phone", True),
        ],
        ids=["unknown-device", "wrong-session", "expired-session"],
    )
    async def test_non_members_are_403(self, db, session_id, device_id, expired):
        _session_with_device(db, expired=expired)

        with pytest.raises(HTTPException) as exc_info:
            await require_session_member(session_id, device_id, db)

        assert _status(exc_info) == 403


class TestRequireHostOrSessionMember:
    @pytest.mark.asyncio
    async def test_any_account_is_accepted(self, db):
        user = _user(db)

        context = await require_host_or_session_member(
            _bearer(create_access_token(user)), None, None, db
        )

        assert context.user.id == user.id
        assert context.device is None

    @pytest.mark.asyncio
    async def test_session_member_is_accepted_without_a_token(self, db):
        _session_with_device(db)

        context = await require_host_or_session_member(None, "ABCD", "phone", db)

        assert context.user is None
        assert context.device.device_id == "phone"
        assert context.session_id == "ABCD"

    @pytest.mark.asyncio
    async def test_a_bad_token_is_not_rescued_by_session_headers(self, db):
        _session_with_device(db)

        with pytest.raises(HTTPException) as exc_info:
            await require_host_or_session_member(
                _bearer("not-a-jwt"), "ABCD", "phone", db
            )

        assert _status(exc_info) == 401

    @pytest.mark.asyncio
    async def test_neither_is_403(self, db):
        with pytest.raises(HTTPException) as exc_info:
            await require_host_or_session_member(None, None, None, db)

        assert _status(exc_info) == 403


def test_get_db_rolls_back_and_reraises_on_error():
    sessions = get_db()
    db = next(sessions)
    db.add(User(username="half-written"))
    db.flush()

    with pytest.raises(RuntimeError):
        sessions.throw(RuntimeError("endpoint failed"))

    check = get_db()
    assert next(check).query(User).filter_by(username="half-written").first() is None
    check.close()
