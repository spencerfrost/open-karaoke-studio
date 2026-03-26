"""
FastAPI router for user management endpoints.
"""

import logging
from typing import Optional

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_user, get_db, require_admin
from app.db.models import User
from app.limiter import limiter
from app.services.auth_service import create_access_token
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


class RegisterUserRequest(BaseModel):
    """Request model for user registration."""
    username: str = Field(..., min_length=1, max_length=100, description="Username")
    display_name: Optional[str] = Field(None, max_length=200, description="Display name")
    password: str = Field(..., min_length=8, description="Password")


class LoginUserRequest(BaseModel):
    """Request model for user login."""
    username: str = Field(..., min_length=1, max_length=100, description="Username")
    password: str = Field(..., description="Password")


class UpdateUserRequest(BaseModel):
    """Request model for updating user."""
    display_name: Optional[str] = Field(None, max_length=200, description="New display name")
    password: Optional[str] = Field(None, min_length=8, description="New password")


class RegisterResponse(BaseModel):
    """Response model for user registration."""
    success: bool
    id: str


class LoginResponse(BaseModel):
    """Response model for user login."""
    success: bool
    id: str
    display_name: Optional[str] = None
    token: str
    is_admin: bool = False
    is_host: bool = False


class UpdateResponse(BaseModel):
    """Response model for user update."""
    success: bool


class UserListItem(BaseModel):
    """User info for admin listing."""
    id: int
    username: str
    display_name: Optional[str]
    is_admin: bool
    is_host: bool


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit("3/minute")
async def register_user(request: Request, body: RegisterUserRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    try:
        if db.query(User).filter(User.username == body.username).first():
            raise HTTPException(
                status_code=400,
                detail="Username already exists"
            )

        user = User(
            username=body.username,
            display_name=body.display_name
        )
        user.set_password(body.password)

        db.add(user)
        db.commit()

        return RegisterResponse(success=True, id=str(user.id))

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to register user: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register user: {str(e)}"
        )


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login_user(request: Request, body: LoginUserRequest, db: Session = Depends(get_db)):
    """Log in a user."""
    try:
        user = db.query(User).filter(User.username == body.username).first()

        if not user or not user.check_password(body.password):
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )

        token = create_access_token(user)

        return LoginResponse(
            success=True,
            id=str(user.id),
            display_name=user.display_name,
            token=token,
            is_admin=user.is_admin,
            is_host=user.is_host,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to login user: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to login: {str(e)}"
        )


@router.patch("/{user_id}", response_model=UpdateResponse)
async def update_user(
    user_id: int,
    body: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update user preferences like display name or password.
    Requires authentication. Users can only update their own account unless they are an admin.
    """
    if body.display_name is None and body.password is None:
        raise HTTPException(
            status_code=400,
            detail="At least one field must be provided for update"
        )

    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own account"
        )

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        if body.display_name is not None:
            user.display_name = body.display_name

        if body.password is not None:
            user.set_password(body.password)

        db.commit()

        return UpdateResponse(success=True)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to update user: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update user: {str(e)}"
        )


@router.get("", response_model=List[UserListItem])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all users. Admin only."""
    users = db.query(User).order_by(User.id).all()
    return [
        UserListItem(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            is_admin=u.is_admin,
            is_host=u.is_host,
        )
        for u in users
    ]


@router.post("/{user_id}/set-host", response_model=UpdateResponse)
async def set_user_host(
    user_id: int,
    is_host: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Toggle is_host on a user. Admin only."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_host = is_host
    db.commit()
    logger.info("Admin %s set user %s is_host=%s", current_user.username, user.username, is_host)
    return UpdateResponse(success=True)
