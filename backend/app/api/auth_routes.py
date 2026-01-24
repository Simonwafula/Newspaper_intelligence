from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.auth import (
    create_access_token,
    get_current_active_user,
    get_password_hash,
    verify_password,
)
from app.db.database import get_db
from app.models import User
from app.schemas import Token, UserResponse
from app.settings import settings
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


def user_to_response(user: User) -> UserResponse:
    """Convert User model to UserResponse schema."""
    return UserResponse.model_validate({
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at,
        "last_login": user.last_login
    })





@router.post("/login", response_model=Token)
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT token."""
    # Find user by email (username field in OAuth2PasswordRequestForm)
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, str(user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not bool(user.is_active):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role},
        expires_delta=access_token_expires
    )

    # Update last login
    db.query(User).filter(User.id == user.id).update({"last_login": datetime.now(UTC)})
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user_role": user.role
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Get current user information."""
    return user_to_response(current_user)


@router.post("/logout")
async def logout_user(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Logout user (client-side token removal)."""
    # JWT tokens are stateless, so we just return success
    # Client should remove the token from storage
    return {"message": "Successfully logged out"}


@router.put("/verify-email")
async def verify_email(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Verify user email (simplified - in production, use email verification tokens)."""
    if bool(current_user.is_verified):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )

    db.query(User).filter(User.id == current_user.id).update({"is_verified": True})
    db.commit()

    return {"message": "Email verified successfully"}


@router.put("/password")
async def change_password(
    password_data: PasswordChange,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Change user password."""
    # Verify current password
    if not verify_password(password_data.current_password, str(current_user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Update password
    new_hash = get_password_hash(password_data.new_password)
    db.query(User).filter(User.id == current_user.id).update({"hashed_password": new_hash})
    db.commit()

    return {"message": "Password changed successfully"}
