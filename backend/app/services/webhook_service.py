"""
Webhook service for triggering and delivering webhook notifications.
"""

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from app.models import Webhook, WebhookDelivery, WebhookEventType

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for managing and triggering webhooks."""

    def __init__(self, db: Session):
        self.db = db

    def create_signature(self, payload: str, secret: str) -> str:
        """Create HMAC-SHA256 signature for webhook payload."""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def get_active_webhooks_for_event(self, event_type: str) -> list[Webhook]:
        """Get all active webhooks subscribed to a specific event type."""
        webhooks = (
            self.db.query(Webhook)
            .filter(
                Webhook.is_active == True,  # noqa: E712
                Webhook.consecutive_failures < 10  # Disable after 10 consecutive failures
            )
            .all()
        )

        # Filter by event type (stored as JSON array)
        return [
            webhook for webhook in webhooks
            if event_type in (webhook.events or [])
        ]

    def create_delivery(
        self,
        webhook: Webhook,
        event_type: str,
        payload: dict
    ) -> WebhookDelivery:
        """Create a webhook delivery record."""
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type=event_type,
            payload=payload,
            status="pending"
        )
        self.db.add(delivery)
        self.db.commit()
        self.db.refresh(delivery)
        return delivery

    async def deliver_webhook(
        self,
        delivery: WebhookDelivery,
        webhook: Webhook
    ) -> bool:
        """
        Attempt to deliver a webhook.

        Returns True if successful, False otherwise.
        """
        payload_json = json.dumps(delivery.payload, default=str)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": delivery.event_type,
            "X-Webhook-Delivery-Id": str(delivery.id),
            "X-Webhook-Timestamp": datetime.now(UTC).isoformat(),
        }

        # Add signature if secret is configured
        if webhook.secret:
            signature = self.create_signature(payload_json, webhook.secret)
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        delivery.attempts += 1

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook.url,
                    content=payload_json,
                    headers=headers,
                    timeout=webhook.timeout_seconds
                )

            delivery.response_status_code = response.status_code
            delivery.response_body = response.text[:1000] if response.text else None

            if 200 <= response.status_code < 300:
                delivery.status = "success"
                delivery.delivered_at = datetime.now(UTC)

                # Update webhook stats
                webhook.last_triggered_at = datetime.now(UTC)
                webhook.last_success_at = datetime.now(UTC)
                webhook.consecutive_failures = 0
                webhook.total_deliveries += 1
                webhook.successful_deliveries += 1

                self.db.commit()
                logger.info(f"Webhook {webhook.id} delivered successfully to {webhook.url}")
                return True
            else:
                delivery.status = "failed"
                delivery.error_message = f"HTTP {response.status_code}: {response.text[:200]}"

                # Update webhook failure stats
                webhook.last_triggered_at = datetime.now(UTC)
                webhook.last_failure_at = datetime.now(UTC)
                webhook.consecutive_failures += 1
                webhook.total_deliveries += 1

                self.db.commit()
                logger.warning(
                    f"Webhook {webhook.id} delivery failed: HTTP {response.status_code}"
                )
                return False

        except httpx.TimeoutException:
            delivery.status = "failed"
            delivery.error_message = "Request timed out"
            webhook.consecutive_failures += 1
            webhook.last_failure_at = datetime.now(UTC)
            self.db.commit()
            logger.error(f"Webhook {webhook.id} timed out")
            return False

        except Exception as e:
            delivery.status = "failed"
            delivery.error_message = str(e)[:500]
            webhook.consecutive_failures += 1
            webhook.last_failure_at = datetime.now(UTC)
            self.db.commit()
            logger.error(f"Webhook {webhook.id} delivery error: {e}")
            return False

    async def trigger_event(
        self,
        event_type: str,
        payload: dict
    ) -> list[WebhookDelivery]:
        """
        Trigger webhooks for a specific event.

        Returns list of delivery records created.
        """
        webhooks = self.get_active_webhooks_for_event(event_type)
        deliveries = []

        for webhook in webhooks:
            delivery = self.create_delivery(webhook, event_type, payload)
            deliveries.append(delivery)

            # Attempt delivery (fire and forget for now)
            try:
                await self.deliver_webhook(delivery, webhook)
            except Exception as e:
                logger.error(f"Error triggering webhook {webhook.id}: {e}")

        return deliveries

    # Convenience methods for specific events

    async def trigger_edition_created(self, edition_id: int, newspaper_name: str, edition_date: str):
        """Trigger webhook when a new edition is created."""
        return await self.trigger_event(
            WebhookEventType.EDITION_CREATED.value,
            {
                "event": "edition.created",
                "edition_id": edition_id,
                "newspaper_name": newspaper_name,
                "edition_date": edition_date,
                "timestamp": datetime.now(UTC).isoformat()
            }
        )

    async def trigger_edition_processed(
        self,
        edition_id: int,
        newspaper_name: str,
        num_pages: int,
        total_items: int,
        items_by_type: dict
    ):
        """Trigger webhook when an edition finishes processing."""
        return await self.trigger_event(
            WebhookEventType.EDITION_PROCESSED.value,
            {
                "event": "edition.processed",
                "edition_id": edition_id,
                "newspaper_name": newspaper_name,
                "num_pages": num_pages,
                "total_items": total_items,
                "items_by_type": items_by_type,
                "timestamp": datetime.now(UTC).isoformat()
            }
        )

    async def trigger_edition_failed(self, edition_id: int, error_message: str):
        """Trigger webhook when edition processing fails."""
        return await self.trigger_event(
            WebhookEventType.EDITION_FAILED.value,
            {
                "event": "edition.failed",
                "edition_id": edition_id,
                "error_message": error_message,
                "timestamp": datetime.now(UTC).isoformat()
            }
        )

    async def trigger_new_jobs(self, edition_id: int, jobs: list[dict]):
        """Trigger webhook when new job listings are extracted."""
        if not jobs:
            return []

        return await self.trigger_event(
            WebhookEventType.NEW_JOBS.value,
            {
                "event": "items.new_jobs",
                "edition_id": edition_id,
                "count": len(jobs),
                "jobs": jobs,
                "timestamp": datetime.now(UTC).isoformat()
            }
        )

    async def trigger_new_tenders(self, edition_id: int, tenders: list[dict]):
        """Trigger webhook when new tender notices are extracted."""
        if not tenders:
            return []

        return await self.trigger_event(
            WebhookEventType.NEW_TENDERS.value,
            {
                "event": "items.new_tenders",
                "edition_id": edition_id,
                "count": len(tenders),
                "tenders": tenders,
                "timestamp": datetime.now(UTC).isoformat()
            }
        )


def get_webhook_service(db: Session) -> WebhookService:
    """Factory function to create WebhookService instance."""
    return WebhookService(db)
