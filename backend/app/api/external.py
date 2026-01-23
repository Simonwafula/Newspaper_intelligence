"""
External API router for third-party application access with API key authentication and rate limiting.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models import Edition, Item, User, UserAPIKey

router = APIRouter(prefix="/external", tags=["external-api"])

# API Key Authentication
security = HTTPBearer(auto_error=False)


class APIKeyManager:
    """Manages API key authentication and rate limiting."""

    def __init__(self, db: Session):
        self.db = db
        self.request_counts: dict[str, list[float]] = {}  # key_hash -> [timestamp, ...]

    def hash_api_key(self, api_key: str) -> str:
        """Create SHA-256 hash of API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def generate_api_key(self, user_id: int, name: str, description: str = None) -> str:
        """Generate a new API key for a user."""
        # Generate secure random key
        api_key = f"mag_newspaper_{secrets.token_urlsafe(32)}"
        key_hash = self.hash_api_key(api_key)

        # Store in database
        db_key = UserAPIKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=api_key[:10],  # First 10 chars for identification
            description=description,
            expires_at=datetime.now(UTC) + timedelta(days=365),  # 1 year expiry
            created_from_ip="system",
            user_agent="system_generated"
        )

        self.db.add(db_key)
        self.db.commit()
        self.db.refresh(db_key)

        return api_key

    def verify_api_key(self, api_key: str) -> UserAPIKey | None:
        """Verify API key and return key details if valid."""
        key_hash = self.hash_api_key(api_key)

        # Find active key in database
        api_key_record = (
            self.db.query(UserAPIKey)
            .filter(
                and_(
                    UserAPIKey.key_hash == key_hash,
                    UserAPIKey.is_active,
                    or_(
                        UserAPIKey.expires_at.is_(None),
                        UserAPIKey.expires_at > datetime.now(UTC)
                    )
                )
            )
            .first()
        )

        if not api_key_record:
            return None

        # Update last used timestamp and request count
        api_key_record.last_used_at = datetime.now(UTC)
        api_key_record.total_requests += 1
        self.db.commit()

        return api_key_record

    def check_rate_limit(self, api_key_record: UserAPIKey) -> bool:
        """Check if API key is within rate limits."""
        now = datetime.now(UTC)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        # Clean old entries from request tracking
        key_hash = api_key_record.key_hash
        if key_hash in self.request_counts:
            # Remove old timestamps
            self.request_counts[key_hash] = [
                ts for ts in self.request_counts[key_hash]
                if ts > hour_ago.timestamp()
            ]

        # Get current request count for this key
        current_requests = len(self.request_counts.get(key_hash, []))

        # Check hourly rate limit
        if current_requests >= api_key_record.rate_limit_per_hour:
            return False

        # Check daily rate limit
        day_requests = len([
            ts for ts in self.request_counts.get(key_hash, [])
            if ts > day_ago.timestamp()
        ])

        if day_requests >= api_key_record.rate_limit_per_day:
            return False

        # Add current request timestamp
        if key_hash not in self.request_counts:
            self.request_counts[key_hash] = []
        self.request_counts[key_hash].append(now.timestamp())

        return True


# Dependency to get API key manager
def get_api_key_manager(db: Session = Depends(get_db)) -> APIKeyManager:
    return APIKeyManager(db)


# Dependency to authenticate via API key
async def get_api_key_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    manager: APIKeyManager = Depends(get_api_key_manager)
) -> User:
    """
    Authenticate user via API key from Authorization header.

    Expected format: Bearer <api_key>
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key = credentials.credentials
    api_key_record = manager.verify_api_key(api_key)

    if not api_key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check rate limits
    if not manager.check_rate_limit(api_key_record):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(api_key_record.rate_limit_per_hour),
                "X-RateLimit-Remaining": str(max(0, api_key_record.rate_limit_per_hour - len(
                    manager.request_counts.get(api_key_record.key_hash, [])
                ))),
            },
        )

    return api_key_record.user


# API Key Management Endpoints
@router.post("/keys/generate")
async def generate_api_key(
    name: str,
    description: str = None,
    permissions: list[str] = None,
    rate_limit_per_hour: int = Query(default=1000, ge=1, le=10000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a new API key for the authenticated user.
    """
    if permissions is None:
        permissions = []
    manager = APIKeyManager(db)

    # Check user's existing keys
    existing_keys = db.query(UserAPIKey).filter(
        UserAPIKey.user_id == current_user.id,
        UserAPIKey.is_active
    ).count()

    max_keys_per_user = 10
    if existing_keys >= max_keys_per_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {max_keys_per_user} API keys per user"
        )

    # Generate new key
    api_key = manager.generate_api_key(
        user_id=current_user.id,
        name=name,
        description=description
    )

    return {
        "message": "API key generated successfully",
        "api_key": api_key,  # Only return full key once
        "key_id": f"{api_key[:10]}...",  # Show prefix for identification
        "name": name,
        "description": description,
        "rate_limit_per_hour": rate_limit_per_hour,
        "expires_at": (datetime.now(UTC) + timedelta(days=365)).isoformat()
    }


@router.get("/keys")
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all API keys for the authenticated user."""
    keys = (
        db.query(UserAPIKey)
        .filter(UserAPIKey.user_id == current_user.id)
        .order_by(desc(UserAPIKey.created_at))
        .all()
    )

    result = []
    for key in keys:
        result.append({
            "id": key.id,
            "name": key.name,
            "description": key.description,
            "key_prefix": key.key_prefix,
            "permissions": key.permissions,
            "rate_limit_per_hour": key.rate_limit_per_hour,
            "rate_limit_per_day": key.rate_limit_per_day,
            "is_active": key.is_active,
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
            "total_requests": key.total_requests,
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            "created_at": key.created_at.isoformat()
        })

    return {"keys": result}


@router.delete("/keys/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an API key."""
    api_key = db.query(UserAPIKey).filter(
        UserAPIKey.id == key_id,
        UserAPIKey.user_id == current_user.id
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    db.delete(api_key)
    db.commit()

    return {"message": "API key deleted successfully"}


# External Data Access Endpoints
@router.get("/editions")
async def get_editions(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    date_from: str = None,
    date_to: str = None,
    newspaper: str = None,
    api_user: User = Depends(get_api_key_user),
    db: Session = Depends(get_db)
):
    """
    Get list of newspaper editions.

    Returns basic metadata only (no full content).
    """
    query = db.query(Edition)

    # Add date filters
    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(Edition.edition_date >= from_date)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid date_from format") from e

    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(Edition.edition_date <= to_date)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid date_to format") from e

    # Add newspaper filter
    if newspaper:
        query = query.filter(Edition.newspaper_name.ilike(f"%{newspaper}%"))

    # Order and paginate
    editions = query.order_by(desc(Edition.edition_date)).offset(offset).limit(limit).all()

    result = []
    for edition in editions:
        result.append({
            "id": edition.id,
            "newspaper_name": edition.newspaper_name,
            "edition_date": edition.edition_date.isoformat(),
            "num_pages": edition.num_pages,
            "status": edition.status,
            "created_at": edition.created_at.isoformat()
        })

    return {
        "editions": result,
        "total": len(editions),
        "limit": limit,
        "offset": offset
    }


@router.get("/editions/{edition_id}/items")
async def get_edition_items(
    edition_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    item_type: str = None,
    subtype: str = None,
    api_user: User = Depends(get_api_key_user),
    db: Session = Depends(get_db)
):
    """
    Get items from a specific edition.

    Returns full content for authorized API access.
    """
    # Verify edition exists
    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        raise HTTPException(status_code=404, detail="Edition not found")

    # Build item query
    query = db.query(Item).filter(Item.edition_id == edition_id)

    # Add type filters
    if item_type:
        query = query.filter(Item.item_type == item_type)

    if subtype:
        query = query.filter(Item.subtype == subtype)

    # Order and paginate
    items = query.order_by(Item.page_number, Item.id).offset(offset).limit(limit).all()

    result = []
    for item in items:
        item_data = {
            "id": item.id,
            "edition_id": item.edition_id,
            "page_number": item.page_number,
            "item_type": item.item_type,
            "subtype": item.subtype if item.subtype else None,
            "title": item.title,
            "text": item.text,
            "structured_data": item.structured_data,
            "created_at": item.created_at.isoformat()
        }

        # Include legacy structured fields for backward compatibility
        if item.contact_info_json:
            item_data["contact_info"] = item.contact_info_json
        if item.price_info_json:
            item_data["price_info"] = item.price_info_json
        if item.date_info_json:
            item_data["date_info"] = item.date_info_json
        if item.location_info_json:
            item_data["location_info"] = item.location_info_json
        if item.classification_details_json:
            item_data["classification_details"] = item.classification_details_json

        result.append(item_data)

    return {
        "edition_info": {
            "id": edition.id,
            "newspaper_name": edition.newspaper_name,
            "edition_date": edition.edition_date.isoformat(),
            "num_pages": edition.num_pages,
            "status": edition.status
        },
        "items": result,
        "total": len(items),
        "limit": limit,
        "offset": offset
    }


@router.get("/search")
async def search_items(
    q: str = Query(..., min_length=2),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    item_type: str = None,
    subtype: str = None,
    date_from: str = None,
    date_to: str = None,
    api_user: User = Depends(get_api_key_user),
    db: Session = Depends(get_db)
):
    """
    Full-text search across all editions and items.

    Searches through titles and text content.
    """
    # Get all items with their editions
    items_query = (
        db.query(Item, Edition)
        .join(Edition, Item.edition_id == Edition.id)
        .filter(Item.text.ilike(f"%{q}%"))
    )

    # Add type filters
    if item_type:
        items_query = items_query.filter(Item.item_type == item_type)

    if subtype:
        items_query = items_query.filter(Item.subtype == subtype)

    # Add date filters
    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            items_query = items_query.filter(Item.created_at >= from_date)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid date_from format") from e

    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            items_query = items_query.filter(Item.created_at <= to_date)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid date_to format") from e

    # Order and paginate
    items = items_query.order_by(desc(Item.created_at)).offset(offset).limit(limit).all()

    result = []
    for item, edition in items:
        item_data = {
            "id": item.id,
            "edition": {
                "id": edition.id,
                "newspaper_name": edition.newspaper_name,
                "edition_date": edition.edition_date.isoformat()
            },
            "page_number": item.page_number,
            "item_type": item.item_type,
            "subtype": item.subtype if item.subtype else None,
            "title": item.title,
            "text": item.text,
            "structured_data": item.structured_data,
            "created_at": item.created_at.isoformat()
        }

        # Include legacy structured fields for backward compatibility
        if item.contact_info_json:
            item_data["contact_info"] = item.contact_info_json
        if item.price_info_json:
            item_data["price_info"] = item.price_info_json
        if item.date_info_json:
            item_data["date_info"] = item.date_info_json
        if item.location_info_json:
            item_data["location_info"] = item.location_info_json
        if item.classification_details_json:
            item_data["classification_details"] = item.classification_details_json

        result.append(item_data)

    return {
        "query": q,
        "items": result,
        "total": len(items),
        "limit": limit,
        "offset": offset
    }


@router.get("/stats")
async def get_api_stats(
    api_user: User = Depends(get_api_key_user),
    db: Session = Depends(get_db)
):
    """
    Get API usage statistics for the authenticated user.
    """
    # Get user's API keys and usage
    api_keys = db.query(UserAPIKey).filter(
        UserAPIKey.user_id == api_user.id,
        UserAPIKey.is_active
    ).all()

    total_requests = sum(key.total_requests for key in api_keys)
    last_used = max((key.last_used_at for key in api_keys if key.last_used_at), default=None)

    return {
        "user_id": api_user.id,
        "email": api_user.email,
        "active_keys": len(api_keys),
        "total_requests": total_requests,
        "last_used": last_used.isoformat() if last_used else None,
        "api_info": {
            "version": "1.0.0",
            "endpoints": [
                "GET /external/editions",
                "GET /external/editions/{id}/items",
                "GET /external/search",
                "GET /external/stats"
            ],
            "documentation": "https://api.example.com/docs"
        }
    }
