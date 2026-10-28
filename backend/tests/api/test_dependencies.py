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
    RequesterContext,
    ensure_session_access,
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
from app.ws.jobs import _credentials_valid


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
    async def test_a_bad_token_falls_back_to_the_session_credential(self, db):
        """A guest's stale host token doesn't cost them their session."""
        _session_with_device(db)

        context = await require_host_or_session_member(
            _bearer("not-a-jwt"), "ABCD", "phone", db
        )

        assert context.user is None
        assert context.session_id == "ABCD"

    @pytest.mark.asyncio
    async def test_a_bad_token_without_a_session_credential_is_401(self, db):
        with pytest.raises(HTTPException) as exc_info:
            await require_host_or_session_member(_bearer("not-a-jwt"), None, None, db)

        assert _status(exc_info) == 401

    @pytest.mark.asyncio
    async def test_a_bad_token_and_a_bad_device_is_401(self, db):
        """The token's error wins, so the client knows to sign out."""
        _session_with_device(db)

        with pytest.raises(HTTPException) as exc_info:
            await require_host_or_session_member(
                _bearer("not-a-jwt"), "ABCD", "someone-else", db
            )

        assert _status(exc_info) == 401

    @pytest.mark.asyncio
    async def test_an_account_and_a_device_are_both_kept(self, db):
        user = _user(db)
        _session_with_device(db)

        context = await require_host_or_session_member(
            _bearer(create_access_token(user)), "ABCD", "phone", db
        )

        assert context.user.id == user.id
        assert context.device.device_id == "phone"
        assert context.session_id == "ABCD"

    @pytest.mark.asyncio
    async def test_non_member_headers_without_a_token_are_403(self, db):
        _session_with_device(db)

        with pytest.raises(HTTPException) as exc_info:
            await require_host_or_session_member(None, "ABCD", "someone-else", db)

        assert _status(exc_info) == 403

    @pytest.mark.asyncio
    async def test_neither_is_403(self, db):
        with pytest.raises(HTTPException) as exc_info:
            await require_host_or_session_member(None, None, None, db)

        assert _status(exc_info) == 403


class TestEnsureSessionAccess:
    """Who may act inside a session: its devices, its host, or an admin."""

    def _hosted(self, db, host):
        _session_with_device(db)
        session = db.query(KaraokeSession).filter_by(session_id="ABCD").one()
        session.host_user_id = host.id
        db.commit()

    def test_a_member_device_may(self, db):
        _session_with_device(db)

        ensure_session_access(RequesterContext(session_id="ABCD"), "ABCD", db)

    def test_the_hosting_account_may(self, db):
        host = _user(db, "host", is_host=True)
        self._hosted(db, host)

        ensure_session_access(RequesterContext(user=host), "ABCD", db)

    def test_an_admin_may(self, db):
        host = _user(db, "host", is_host=True)
        self._hosted(db, host)
        admin = _user(db, "admin", is_admin=True)

        ensure_session_access(RequesterContext(user=admin), "ABCD", db)

    @pytest.mark.parametrize(
        "who",
        ["plain-account", "other-host", "demo-host", "other-session-device"],
    )
    def test_anyone_else_is_403(self, db, who):
        host = _user(db, "host", is_host=True)
        self._hosted(db, host)
        if who == "other-session-device":
            requester = RequesterContext(session_id="WXYZ")
        else:
            roles = {
                "plain-account": {},
                "other-host": {"is_host": True},
                "demo-host": {"is_host": True, "is_demo": True},
            }[who]
            requester = RequesterContext(user=_user(db, who, **roles))

        with pytest.raises(HTTPException) as exc_info:
            ensure_session_access(requester, "ABCD", db)

        assert _status(exc_info) == 403

    def test_a_missing_session_looks_like_someone_elses(self, db):
        user = _user(db, "host", is_host=True)

        with pytest.raises(HTTPException) as exc_info:
            ensure_session_access(RequesterContext(user=user), "NOPE", db)

        assert _status(exc_info) == 403


class TestJobsSocketCredentials:
    """The /ws/jobs authenticate message takes the same credentials as REST."""

    def test_an_account_token_is_accepted(self, db):
        user = _user(db)

        assert _credentials_valid({"token": create_access_token(user)})

    def test_a_session_member_is_accepted(self, db):
        _session_with_device(db)

        assert _credentials_valid({"session_id": "ABCD", "device_id": "phone"})

    @pytest.mark.parametrize(
        "message",
        [
            {},
            {"token": "not-a-jwt"},
            {"session_id": "ABCD", "device_id": "someone-else"},
            {"session_id": "ABCD"},
            {"device_id": "phone"},
        ],
        ids=["nothing", "bad-token", "not-a-member", "no-device", "no-session"],
    )
    def test_anything_else_is_refused(self, db, message):
        _session_with_device(db)

        assert not _credentials_valid(message)

    def test_a_deleted_users_token_is_refused(self, db):
        user = _user(db)
        token = create_access_token(user)
        db.delete(user)
        db.commit()

        assert not _credentials_valid({"token": token})


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
