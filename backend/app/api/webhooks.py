"""
Webhook management API endpoints.
"""

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models import User, Webhook, WebhookDelivery, WebhookEventType

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# Schemas
class WebhookCreate(BaseModel):
    """Schema for creating a new webhook."""
    name: str = Field(..., min_length=1, max_length=100)
    url: HttpUrl
    events: list[str] = Field(..., min_length=1)
    secret: str | None = None  # If not provided, one will be generated
    retry_count: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=30, ge=5, le=120)


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook."""
    name: str | None = None
    url: HttpUrl | None = None
    events: list[str] | None = None
    is_active: bool | None = None
    retry_count: int | None = Field(None, ge=0, le=10)
    timeout_seconds: int | None = Field(None, ge=5, le=120)


class WebhookResponse(BaseModel):
    """Schema for webhook response."""
    id: int
    name: str
    url: str
    events: list[str]
    is_active: bool
    retry_count: int
    timeout_seconds: int
    last_triggered_at: datetime | None
    last_success_at: datetime | None
    last_failure_at: datetime | None
    consecutive_failures: int
    total_deliveries: int
    successful_deliveries: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookWithSecret(WebhookResponse):
    """Webhook response including secret (only shown on creation)."""
    secret: str | None


class WebhookDeliveryResponse(BaseModel):
    """Schema for webhook delivery response."""
    id: int
    webhook_id: int
    event_type: str
    payload: dict
    status: str
    attempts: int
    response_status_code: int | None
    error_message: str | None
    created_at: datetime
    delivered_at: datetime | None

    class Config:
        from_attributes = True


class WebhookTestResponse(BaseModel):
    """Response from testing a webhook."""
    success: bool
    status_code: int | None
    response_body: str | None
    error_message: str | None


# Endpoints

@router.get("/events", response_model=list[dict])
async def list_webhook_events():
    """
    List all available webhook event types.

    Returns the event types that can be subscribed to.
    """
    return [
        {
            "event": WebhookEventType.EDITION_CREATED.value,
            "description": "Triggered when a new newspaper edition is uploaded"
        },
        {
            "event": WebhookEventType.EDITION_PROCESSED.value,
            "description": "Triggered when edition processing completes successfully"
        },
        {
            "event": WebhookEventType.EDITION_FAILED.value,
            "description": "Triggered when edition processing fails"
        },
        {
            "event": WebhookEventType.ITEMS_EXTRACTED.value,
            "description": "Triggered when items are extracted from an edition"
        },
        {
            "event": WebhookEventType.NEW_JOBS.value,
            "description": "Triggered when new job listings are extracted"
        },
        {
            "event": WebhookEventType.NEW_TENDERS.value,
            "description": "Triggered when new tender notices are extracted"
        }
    ]


@router.post("", response_model=WebhookWithSecret)
async def create_webhook(
    webhook_data: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new webhook subscription.

    The webhook will receive HTTP POST requests when subscribed events occur.
    A secret is generated if not provided - save it securely as it won't be shown again.
    """
    # Validate events
    valid_events = {e.value for e in WebhookEventType}
    for event in webhook_data.events:
        if event not in valid_events:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event type: {event}. Valid events: {list(valid_events)}"
            )

    # Check webhook limit per user
    existing_count = db.query(Webhook).filter(
        Webhook.user_id == current_user.id
    ).count()

    if existing_count >= 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 webhooks per user"
        )

    # Generate secret if not provided
    webhook_secret = webhook_data.secret or secrets.token_urlsafe(32)

    webhook = Webhook(
        user_id=current_user.id,
        name=webhook_data.name,
        url=str(webhook_data.url),
        secret=webhook_secret,
        events=webhook_data.events,
        retry_count=webhook_data.retry_count,
        timeout_seconds=webhook_data.timeout_seconds
    )

    db.add(webhook)
    db.commit()
    db.refresh(webhook)

    return WebhookWithSecret(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        secret=webhook_secret,  # Only shown on creation
        is_active=webhook.is_active,
        retry_count=webhook.retry_count,
        timeout_seconds=webhook.timeout_seconds,
        last_triggered_at=webhook.last_triggered_at,
        last_success_at=webhook.last_success_at,
        last_failure_at=webhook.last_failure_at,
        consecutive_failures=webhook.consecutive_failures,
        total_deliveries=webhook.total_deliveries,
        successful_deliveries=webhook.successful_deliveries,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at
    )


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all webhooks for the current user.
    """
    webhooks = (
        db.query(Webhook)
        .filter(Webhook.user_id == current_user.id)
        .order_by(desc(Webhook.created_at))
        .all()
    )

    return webhooks


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific webhook.
    """
    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == current_user.id
    ).first()

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return webhook


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: int,
    webhook_data: WebhookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a webhook's configuration.
    """
    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == current_user.id
    ).first()

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    # Validate events if provided
    if webhook_data.events is not None:
        valid_events = {e.value for e in WebhookEventType}
        for event in webhook_data.events:
            if event not in valid_events:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid event type: {event}"
                )
        webhook.events = webhook_data.events

    if webhook_data.name is not None:
        webhook.name = webhook_data.name
    if webhook_data.url is not None:
        webhook.url = str(webhook_data.url)
    if webhook_data.is_active is not None:
        webhook.is_active = webhook_data.is_active
        if webhook_data.is_active:
            # Reset failure count when re-enabling
            webhook.consecutive_failures = 0
    if webhook_data.retry_count is not None:
        webhook.retry_count = webhook_data.retry_count
    if webhook_data.timeout_seconds is not None:
        webhook.timeout_seconds = webhook_data.timeout_seconds

    db.commit()
    db.refresh(webhook)

    return webhook


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a webhook.
    """
    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == current_user.id
    ).first()

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    db.delete(webhook)
    db.commit()

    return {"message": "Webhook deleted successfully"}


@router.post("/{webhook_id}/regenerate-secret", response_model=dict)
async def regenerate_webhook_secret(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Regenerate the secret for a webhook.

    The new secret will be returned. Save it securely as it won't be shown again.
    """
    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == current_user.id
    ).first()

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    new_secret = secrets.token_urlsafe(32)
    webhook.secret = new_secret
    db.commit()

    return {
        "message": "Secret regenerated successfully",
        "secret": new_secret
    }


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
async def list_webhook_deliveries(
    webhook_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List delivery history for a webhook.
    """
    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == current_user.id
    ).first()

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    query = db.query(WebhookDelivery).filter(
        WebhookDelivery.webhook_id == webhook_id
    )

    if status:
        query = query.filter(WebhookDelivery.status == status)

    deliveries = (
        query
        .order_by(desc(WebhookDelivery.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return deliveries


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a test event to the webhook.

    This sends a test payload to verify the webhook endpoint is working.
    """
    import httpx

    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == current_user.id
    ).first()

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    # Create test payload
    from datetime import timezone
    import hashlib
    import hmac
    import json

    test_payload = {
        "event": "test",
        "message": "This is a test webhook delivery",
        "webhook_id": webhook.id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    payload_json = json.dumps(test_payload, default=str)

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": "test",
        "X-Webhook-Delivery-Id": "test",
        "X-Webhook-Timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if webhook.secret:
        signature = hmac.new(
            webhook.secret.encode('utf-8'),
            payload_json.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={signature}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook.url,
                content=payload_json,
                headers=headers,
                timeout=webhook.timeout_seconds
            )

        return WebhookTestResponse(
            success=200 <= response.status_code < 300,
            status_code=response.status_code,
            response_body=response.text[:500] if response.text else None,
            error_message=None if 200 <= response.status_code < 300 else f"HTTP {response.status_code}"
        )

    except httpx.TimeoutException:
        return WebhookTestResponse(
            success=False,
            status_code=None,
            response_body=None,
            error_message="Request timed out"
        )
    except Exception as e:
        return WebhookTestResponse(
            success=False,
            status_code=None,
            response_body=None,
            error_message=str(e)[:500]
        )
