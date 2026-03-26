"""
JWT authentication service for Open Karaoke Studio.
"""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
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


def create_access_token(user: User) -> str:
    """Generate a JWT access token for the given user."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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
