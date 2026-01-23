from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_admin_user
from app.db.database import get_db
from app.models import User, UserRole, AccessRequest, AccessRequestStatus
from app.schemas import UserCreate, UserResponse, UserUpdate, AccessRequestResponse, AccessRequestUpdate
from app.services.auth_service import create_user, get_user_by_email
from app.utils.auth import get_password_hash

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_account(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Create a new user account (admin only)."""
    # Check if user already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create the user
    user = create_user(db, user_data)
    return UserResponse.model_validate(user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """List all users (admin only)."""
    users = db.query(User).offset(skip).limit(limit).all()
    return [UserResponse.model_validate(user) for user in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Get specific user details (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_account(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Update user account (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    
    if user_update.password is not None:
        user.hashed_password = get_password_hash(user_update.password)
    
    db.commit()
    db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}")
async def delete_user_account(
    user_id: int,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Delete user account (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}


@router.get("/access-requests", response_model=list[AccessRequestResponse])
async def list_access_requests(
    skip: int = 0,
    limit: int = 50,
    status_filter: AccessRequestStatus | None = None,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """List access requests (admin only)."""
    query = db.query(AccessRequest)
    
    if status_filter:
        query = query.filter(AccessRequest.status == status_filter.value)
    
    requests = query.order_by(AccessRequest.created_at.desc()).offset(skip).limit(limit).all()
    return [AccessRequestResponse.model_validate(req) for req in requests]


@router.put("/access-requests/{request_id}", response_model=AccessRequestResponse)
async def update_access_request(
    request_id: int,
    request_update: AccessRequestUpdate,
    db: Session = Depends(get_db),
    admin_user = Depends(get_admin_user)
):
    """Approve or reject access request (admin only)."""
    access_request = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not access_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access request not found"
        )
    
    if access_request.status != AccessRequestStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access request has already been processed"
        )
    
    # Update the request
    access_request.status = request_update.status.value
    access_request.admin_notes = request_update.admin_notes
    access_request.processed_by_user_id = admin_user.id
    from datetime import datetime
    access_request.processed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(access_request)
    
    # If approved, create user account
    if request_update.status == AccessRequestStatus.APPROVED:
        user_create = UserCreate(
            email=access_request.email,
            password="temp123456",  # Admin should change this
            full_name=access_request.full_name,
            role=UserRole.READER
        )
        
        try:
            new_user = create_user(db, user_create)
            return AccessRequestResponse.model_validate(access_request)
        except Exception as e:
            # Rollback access request approval if user creation fails
            access_request.status = AccessRequestStatus.PENDING.value
            access_request.admin_notes = f"Failed to create user: {str(e)}"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user account"
            )
    
    return AccessRequestResponse.model_validate(access_request)