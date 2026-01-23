from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserCreate, UserUpdate
from app.settings import settings
from app.utils.auth import create_access_token, get_password_hash, verify_password


def get_user_by_email(db: Session, email: str) -> User | None:
    """
    Get a user by email address.

    Args:
        db: Database session
        email: User email address

    Returns:
        User object if found, None otherwise
    """
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """
    Get a user by ID.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        User object if found, None otherwise
    """
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_create: UserCreate) -> User:
    """
    Create a new user with hashed password.

    Args:
        db: Database session
        user_create: User creation data

    Returns:
        Created User object

    Raises:
        HTTPException: If user with email already exists
    """
    # Check if user already exists
    existing_user = get_user_by_email(db, user_create.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Hash the password
    hashed_password = get_password_hash(user_create.password)

    # Create user
    db_user = User(
        email=user_create.email,
        hashed_password=hashed_password,
        full_name=user_create.full_name,
        role=user_create.role.value,
        is_active=True,
        created_at=datetime.now(UTC)
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """
    Authenticate a user by email and password.

    Args:
        db: Database session
        email: User email address
        password: Plain text password

    Returns:
        User object if authenticated, None otherwise
    """
    user = get_user_by_email(db, email)
    if not user:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    # Update last login
    user.last_login = datetime.now(UTC)
    db.commit()

    return user


def create_user_access_token(user: User) -> dict:
    """
    Create an access token for a user.

    Args:
        user: User object

    Returns:
        Token response dictionary
    """
    access_token_expires = settings.access_token_expire_minutes * 60  # Convert to seconds
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": access_token_expires,
        "user_role": user.role
    }


def update_user(db: Session, user: User, user_update: UserUpdate) -> User:
    """
    Update a user's profile.

    Args:
        db: Database session
        user: Existing user object
        user_update: User update data

    Returns:
        Updated User object
    """
    if user_update.full_name is not None:
        user.full_name = user_update.full_name

    if user_update.password is not None:
        user.hashed_password = get_password_hash(user_update.password)

    user.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(user)

    return user


def deactivate_user(db: Session, user: User) -> User:
    """
    Deactivate a user account.

    Args:
        db: Database session
        user: User object to deactivate

    Returns:
        Updated User object
    """
    user.is_active = False
    user.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(user)

    return user


def is_admin(user: User) -> bool:
    """
    Check if a user has admin role.

    Args:
        user: User object

    Returns:
        True if user is admin, False otherwise
    """
    return user.role == "ADMIN"
