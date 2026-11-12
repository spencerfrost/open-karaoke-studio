"""
JWT authentication service for Open Karaoke Studio.
"""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import User

logger = logging.getLogger(__name__)

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 10080)  # 7 days
)


def _get_secret_key() -> str:
    """Get JWT secret key from environment, generating one if not set."""
    key = os.environ.get("JWT_SECRET_KEY")
    if not key:
        key = secrets.token_urlsafe(64)
        os.environ["JWT_SECRET_KEY"] = key
        logger.error(
            "JWT_SECRET_KEY not set — generated a random key. "
            "Set JWT_SECRET_KEY in your .env for stable tokens across restarts."
        )
    return key


def create_access_token(user: User, expires_minutes: Optional[float] = None) -> str:
    """Generate a JWT access token for the given user."""
    if expires_minutes is None:
        expires_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "is_admin": user.is_admin,
        "is_host": user.is_host,
        "exp": expire,
    }
    return jwt.encode(payload, _get_secret_key(), algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Validate a JWT token and return its payload, or None if invalid."""
    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning("JWT verification failed: %s", e)
        return None


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Verify credentials and return the User if valid, or None."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not user.check_password(password):
        return None
    return user


MIN_ADMIN_PASSWORD_LENGTH = 8  # same minimum as RegisterUserRequest


def ensure_admin_from_env(
    db: Session, username: Optional[str], password: Optional[str]
) -> Optional[User]:
    """Create the first admin from ADMIN_USERNAME / ADMIN_PASSWORD.

    Runs once per API start. Does nothing when neither value is set or when any
    admin already exists. Never promotes an existing account: registration is
    open, so someone could take the name first and gain admin with their own
    password. Returns the created admin, or None when nothing was created.
    """
    username = (username or "").strip()
    password = password or ""
    if not username and not password:
        return None
    if not username or not password:
        missing = "ADMIN_USERNAME" if not username else "ADMIN_PASSWORD"
        logger.warning("%s is not set; skipping the startup admin", missing)
        return None

    if db.query(User).filter(User.is_admin.is_(True)).first():
        logger.debug("An admin already exists; ignoring ADMIN_USERNAME")
        return None

    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        logger.error(
            "ADMIN_PASSWORD must be at least %d characters; no admin created",
            MIN_ADMIN_PASSWORD_LENGTH,
        )
        return None

    if db.query(User).filter(User.username == username).first():
        logger.error(
            "ADMIN_USERNAME '%s' belongs to an existing non-admin account; "
            "not promoting it. Pick another name or use manage_users.py",
            username,
        )
        return None

    try:
        user = User(username=username, display_name=username, is_admin=True)
    except ValueError as e:
        logger.error("ADMIN_USERNAME is invalid (%s); no admin created", e)
        return None
    user.set_password(password)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Another process created the same username between the check and commit.
        db.rollback()
        logger.info("Admin '%s' was created by another process", username)
        return None
    logger.info("Created admin '%s' from ADMIN_USERNAME", username)
    return user
