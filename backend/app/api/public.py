from datetime import UTC, datetime, timedelta
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import AccessRequest, AccessRequestStatus, Edition
from app.schemas import AccessRequestCreate, AccessRequestResponse, EditionPublicResponse
from app.settings import settings

router = APIRouter(prefix="/api/public", tags=["public"])


# Simple in-memory rate limiter for basic protection
# In production, use Redis or similar
_rate_limit_store = {}

def check_rate_limit(request: Request, limit: int = 5, window_minutes: int = 60):
    """Basic rate limiting by IP and email."""
    client_ip = request.client.host if request.client else "unknown"

    # Clean old entries
    now = datetime.now(UTC)
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
    editions = db.query(Edition).filter(
        Edition.status.in_(["READY", "ARCHIVED"])
    ).order_by(
        Edition.edition_date.desc()
    ).offset(skip).limit(limit).all()

    results = []
    for edition in editions:
        cover_path = edition.cover_image_path or os.path.join(
            settings.storage_path, "covers", f"{edition.id}.png"
        )
        cover_url = None
        if os.path.exists(cover_path):
            rel_path = os.path.relpath(cover_path, settings.storage_path)
            cover_url = f"/files/{rel_path.replace(os.sep, '/')}"

        results.append(
            EditionPublicResponse(
                id=edition.id,
                newspaper_name=edition.newspaper_name,
                edition_date=edition.edition_date,
                status=edition.status,
                cover_image_url=cover_url,
            )
        )

    return results


@router.get("/editions/{edition_id}/cover")
async def get_public_cover(
    edition_id: int,
    db: Session = Depends(get_db)
):
    """Return cover image for public access."""
    edition = db.query(Edition).filter(
        Edition.id == edition_id,
        Edition.status.in_(["READY", "ARCHIVED"])
    ).first()

    if not edition:
        raise HTTPException(status_code=404, detail="Edition not found")

    cover_path = edition.cover_image_path or os.path.join(
        settings.storage_path, "covers", f"{edition.id}.png"
    )
    if not os.path.exists(cover_path):
        raise HTTPException(status_code=404, detail="Cover not found")

    return FileResponse(cover_path)


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
