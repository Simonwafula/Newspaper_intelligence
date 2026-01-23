from typing import Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.database import get_db
from app.models import Edition, AccessRequest, AccessRequestStatus
from app.schemas import EditionPublicResponse, AccessRequestCreate, AccessRequestResponse

router = APIRouter()


# Simple in-memory rate limiter for basic protection
# In production, use Redis or similar
_rate_limit_store = {}

def check_rate_limit(request: Request, limit: int = 5, window_minutes: int = 60):
    """Basic rate limiting by IP and email."""
    client_ip = request.client.host if request.client else "unknown"
    
    # Clean old entries
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=window_minutes)
    
    # Check IP limit
    if client_ip in _rate_limit_store:
        _rate_limit_store[client_ip] = [
            timestamp for timestamp in _rate_limit_store[client_ip]
            if timestamp > cutoff
        ]
        if len(_rate_limit_store[client_ip]) >= limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later."
            )
    else:
        _rate_limit_store[client_ip] = []
    
    _rate_limit_store[client_ip].append(now)


@router.get("/editions", response_model=list[EditionPublicResponse])
async def list_public_editions(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List newspaper editions with public information only.
    
    Provides basic edition information (covers-only access) without requiring authentication.
    Includes newspaper name, date, status, and page count but no processing details.
    
    Args:
        skip: Number of editions to skip (pagination)
        limit: Maximum number of editions to return
        db: Database session
        
    Returns:
        List of public edition information
    """
    # Query only public-safe fields
    editions = db.query(Edition).filter(
        # Only show READY editions to public
        Edition.status == "READY"
    ).order_by(
        Edition.edition_date.desc()
    ).offset(skip).limit(limit).all()
    
    return [
        EditionPublicResponse.model_validate(edition)
        for edition in editions
    ]


@router.get("/editions/{edition_id}", response_model=EditionPublicResponse)
async def get_public_edition(
    edition_id: int,
    db: Session = Depends(get_db)
):
    """
    Get public information about a specific edition.
    
    Provides basic edition information without requiring authentication.
    Only works for editions that are in READY status.
    
    Args:
        edition_id: ID of the edition
        db: Database session
        
    Returns:
        Public edition information
        
    Raises:
        HTTPException: If edition not found or not ready
    """
    edition = db.query(Edition).filter(
        Edition.id == edition_id,
        Edition.status == "READY"  # Only show ready editions
    ).first()
    
    if not edition:
        raise HTTPException(status_code=404, detail="Edition not found")
    
    return EditionPublicResponse.model_validate(edition)


@router.post("/access-requests", response_model=AccessRequestResponse)
async def create_access_request(
    request_data: AccessRequestCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Submit a new access request.
    
    Creates an access request that will be reviewed by an administrator.
    Includes basic rate limiting and bot protection.
    
    Args:
        request_data: Access request form data
        request: HTTP request for rate limiting and tracking
        db: Database session
        
    Returns:
        Created access request information
        
    Raises:
        HTTPException: If rate limit exceeded or bot detected
    """
    # Rate limiting
    check_rate_limit(request, limit=3, window_minutes=60)  # 3 requests per hour per IP
    
    # Bot protection - check honeypot field
    if request_data.website_url:
        raise HTTPException(status_code=400, detail="Bot detected")
    
    # Check if there's already a pending request for this email
    existing_request = db.query(AccessRequest).filter(
        and_(
            AccessRequest.email == request_data.email,
            AccessRequest.status == AccessRequestStatus.PENDING.value
        )
    ).first()
    
    if existing_request:
        raise HTTPException(
            status_code=400,
            detail="You already have a pending request. Please wait for review."
        )
    
    # Create the access request
    access_request = AccessRequest(
        full_name=request_data.full_name,
        email=request_data.email,
        organization=request_data.organization,
        phone=request_data.phone,
        reason=request_data.reason,
        consent_not_redistribute=request_data.consent_not_redistribute,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent"),
        honeypot_field=request_data.website_url,  # Store for analysis
        status=AccessRequestStatus.PENDING.value
    )
    
    db.add(access_request)
    db.commit()
    db.refresh(access_request)
    
    return AccessRequestResponse.model_validate(access_request)