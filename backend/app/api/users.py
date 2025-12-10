"""
FastAPI router for user management endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


from app.db import SessionLocal
from app.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


class RegisterUserRequest(BaseModel):
    """Request model for user registration."""
    username: str = Field(..., min_length=1, max_length=100, description="Username")
    display_name: Optional[str] = Field(None, max_length=200, description="Display name")
    password: Optional[str] = Field(None, min_length=4, description="Optional password")


class LoginUserRequest(BaseModel):
    """Request model for user login."""
    username: str = Field(..., min_length=1, max_length=100, description="Username")
    password: Optional[str] = Field(None, description="Password if user has one set")


class UpdateUserRequest(BaseModel):
    """Request model for updating user."""
    display_name: Optional[str] = Field(None, max_length=200, description="New display name")
    password: Optional[str] = Field(None, min_length=4, description="New password")


class RegisterResponse(BaseModel):
    """Response model for user registration."""
    success: bool
    id: str


class LoginResponse(BaseModel):
    """Response model for user login."""
    success: bool
    id: str
    display_name: Optional[str] = None


class UpdateResponse(BaseModel):
    """Response model for user update."""
    success: bool


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register_user(request: RegisterUserRequest):
    """
    Register a new user with an optional password.
    
    If no password is provided, the user can be logged in without one.
    """
    session = SessionLocal()
    try:
        # Check if username already exists
        if session.query(User).filter(User.username == request.username).first():
            raise HTTPException(
                status_code=400,
                detail="Username already exists"
            )

        user = User(
            username=request.username,
            display_name=request.display_name
        )
        
        if request.password:
            user.set_password(request.password)

        session.add(user)
        session.commit()
        
        return RegisterResponse(success=True, id=str(user.id))
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error("Failed to register user: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register user: {str(e)}"
        )
    finally:
        session.close()


@router.post("/login", response_model=LoginResponse)
async def login_user(request: LoginUserRequest):
    """
    Log in a user.
    
    If the user has a password set, the password must be provided.
    If no password is set, the user can log in with just their username.
    """
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == request.username).first()
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        # Check password if user has one set
        has_password = getattr(user, "password_hash", None)
        if has_password:
            if not request.password or not user.check_password(request.password):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid username or password"
                )

        return LoginResponse(
            success=True,
            id=str(user.id),
            display_name=user.display_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to login user: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to login: {str(e)}"
        )
    finally:
        session.close()


@router.patch("/{user_id}", response_model=UpdateResponse)
async def update_user(user_id: int, request: UpdateUserRequest):
    """
    Update user preferences like display name or password.
    """
    # Validate that at least one field is being updated
    if request.display_name is None and request.password is None:
        raise HTTPException(
            status_code=400,
            detail="At least one field must be provided for update"
        )
    
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        if request.display_name is not None:
            user.display_name = request.display_name
            
        if request.password is not None:
            user.set_password(request.password)

        session.commit()
        
        return UpdateResponse(success=True)
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error("Failed to update user: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update user: {str(e)}"
        )
    finally:
        session.close()
