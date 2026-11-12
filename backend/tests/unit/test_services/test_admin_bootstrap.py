"""Tests for creating the first admin from ADMIN_USERNAME / ADMIN_PASSWORD."""

from unittest import mock

import pytest

from app.db.database import SessionLocal
from app.db.models import User
from app.services import auth_service
from app.services.auth_service import ensure_admin_from_env

PASSWORD = "long-enough-pw"


@pytest.fixture
def log():
    """The service's logger. The app's logging config hides it from caplog."""
    with mock.patch.object(auth_service, "logger") as logger:
        yield logger


def _logged(log_method) -> str:
    return " ".join(str(c.args[0] % c.args[1:]) for c in log_method.call_args_list)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _add_user(db, username, *, is_admin=False):
    user = User(username=username, display_name=username, is_admin=is_admin)
    user.set_password("existing-pw")
    db.add(user)
    db.commit()
    return user


def test_does_nothing_when_neither_is_set(db, log):
    assert ensure_admin_from_env(db, None, None) is None
    assert ensure_admin_from_env(db, "", "") is None
    assert db.query(User).count() == 0
    assert log.method_calls == []


@pytest.mark.parametrize(
    "username,password,missing",
    [("admin", None, "ADMIN_PASSWORD"), (None, PASSWORD, "ADMIN_USERNAME")],
)
def test_warns_when_only_one_is_set(db, log, username, password, missing):
    assert ensure_admin_from_env(db, username, password) is None
    assert db.query(User).count() == 0
    assert missing in _logged(log.warning)


def test_creates_admin(db):
    user = ensure_admin_from_env(db, "admin", PASSWORD)

    assert user is not None
    stored = db.query(User).filter(User.username == "admin").one()
    assert stored.is_admin is True
    assert stored.display_name == "admin"
    assert stored.check_password(PASSWORD)


def test_never_logs_the_password(db, log):
    ensure_admin_from_env(db, "admin", PASSWORD)
    assert all(PASSWORD not in str(c) for c in log.mock_calls)
    assert "admin" in _logged(log.info)


def test_skips_when_any_admin_exists(db):
    _add_user(db, "someone-else", is_admin=True)

    assert ensure_admin_from_env(db, "admin", PASSWORD) is None
    assert db.query(User).filter(User.username == "admin").first() is None


def test_running_twice_creates_one_admin(db):
    ensure_admin_from_env(db, "admin", PASSWORD)
    assert ensure_admin_from_env(db, "admin", "a-different-password") is None

    assert db.query(User).count() == 1
    stored = db.query(User).one()
    assert stored.check_password(PASSWORD)


def test_does_not_promote_an_existing_account(db, log):
    _add_user(db, "admin")

    assert ensure_admin_from_env(db, "admin", PASSWORD) is None

    stored = db.query(User).filter(User.username == "admin").one()
    assert stored.is_admin is False
    assert stored.check_password("existing-pw")
    assert "not promoting" in _logged(log.error)


def test_rejects_a_short_password(db, log):
    assert ensure_admin_from_env(db, "admin", "short") is None
    assert db.query(User).count() == 0
    assert "ADMIN_PASSWORD" in _logged(log.error)


def test_rejects_a_short_username(db, log):
    assert ensure_admin_from_env(db, "ab", PASSWORD) is None
    assert db.query(User).count() == 0
    assert "ADMIN_USERNAME" in _logged(log.error)
