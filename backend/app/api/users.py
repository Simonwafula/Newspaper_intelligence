from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas import Token, UserCreate, UserLogin, UserResponse, UserUpdate
from app.services.auth_service import (
    authenticate_user,
    create_user,
    create_user_access_token,
    get_user_by_id,
    update_user,
)
from app.utils.auth import extract_user_id_from_token

router = APIRouter()
security = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Get the currently authenticated user from JWT token.

    Args:
        credentials: HTTP Authorization credentials
        db: Database session

    Returns:
        Current user object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    user_id = extract_user_id_from_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserResponse.model_validate(user)


def get_current_admin_user(
    current_user: Annotated[UserResponse, Depends(get_current_user)]
) -> UserResponse:
    """
    Get the currently authenticated user and ensure they are an admin.

    Args:
        current_user: Current authenticated user

    Returns:
        Current admin user object

    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_create: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user.

    Args:
        user_create: User registration data
        db: Database session

    Returns:
        Created user object

    Raises:
        HTTPException: If user already exists
    """
    user = create_user(db, user_create)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
async def login_user(
    user_login: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate a user and return an access token.

    Args:
        user_login: User login credentials
        db: Database session

    Returns:
        JWT access token

    Raises:
        HTTPException: If credentials are invalid
    """
    user = authenticate_user(db, user_login.email, user_login.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = create_user_access_token(user)
    return Token(**token_data)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: Annotated[UserResponse, Depends(get_current_user)]
):
    """
    Get the current user's profile.

    Args:
        current_user: Current authenticated user

    Returns:
        User profile data
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Update the current user's profile.

    Args:
        user_update: User update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated user profile
    """
    # Get full user object
    user = get_user_by_id(db, current_user.id)
    updated_user = update_user(db, user, user_update)
    return UserResponse.model_validate(updated_user)


@router.post("/logout")
async def logout_user():
    """
    Logout a user.

    Note: JWT tokens are stateless, so actual logout happens on the client side
    by discarding the token. This endpoint exists for consistency and future
    token blacklisting if needed.

    Returns:
        Success message
    """
    return {"message": "Successfully logged out"}
