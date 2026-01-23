"""
Tests for webhook functionality.
"""

import pytest
from app.api.auth import get_current_user
from app.main import app
from app.models import User, UserRole, Webhook
from app.services.webhook_service import WebhookService
from app.utils.auth import create_access_token, get_password_hash


@pytest.fixture
def test_user(db):
    """Create a test user and set up auth override."""
    user = User(
        email="webhook_test@example.com",
        hashed_password=get_password_hash("testpassword"),
        full_name="Webhook Tester",
        role=UserRole.ADMIN.value,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Store user data
    user_data = User(
        id=user.id,
        email=user.email,
        hashed_password=user.hashed_password,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified
    )

    # Override get_current_user to return this user
    async def override_get_current_user():
        return user_data
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    # Create access token
    token = create_access_token({"sub": str(user.id)})
    
    yield {"id": user.id, "token": token, "user": user_data}
    
    # Clear auth override after test
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]


@pytest.fixture
def auth_headers(test_user):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {test_user['token']}"}


class TestWebhookEvents:
    """Tests for webhook event listing."""

    def test_list_webhook_events(self, client):
        """Test listing available webhook events."""
        response = client.get("/api/webhooks/events")
        assert response.status_code == 200
        events = response.json()
        assert len(events) == 6

        event_names = [e["event"] for e in events]
        assert "edition.created" in event_names
        assert "edition.processed" in event_names
        assert "edition.failed" in event_names
        assert "items.new_jobs" in event_names
        assert "items.new_tenders" in event_names


class TestWebhookCRUD:
    """Tests for webhook CRUD operations."""

    def test_create_webhook(self, client, auth_headers):
        """Test creating a new webhook."""
        webhook_data = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["edition.created", "edition.processed"]
        }

        response = client.post(
            "/api/webhooks",
            json=webhook_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Webhook"
        assert data["url"] == "https://example.com/webhook"
        assert "edition.created" in data["events"]
        assert "secret" in data  # Secret shown on creation

    def test_create_webhook_with_invalid_event(self, client, auth_headers):
        """Test creating webhook with invalid event type."""
        webhook_data = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["invalid.event"]
        }

        response = client.post(
            "/api/webhooks",
            json=webhook_data,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "Invalid event type" in response.json()["detail"]

    def test_list_webhooks(self, client, auth_headers):
        """Test listing user's webhooks."""
        # Create a webhook first
        webhook_data = {
            "name": "List Test",
            "url": "https://example.com/webhook",
            "events": ["edition.created"]
        }
        client.post("/api/webhooks", json=webhook_data, headers=auth_headers)

        response = client.get("/api/webhooks", headers=auth_headers)
        assert response.status_code == 200
        webhooks = response.json()
        assert len(webhooks) >= 1
        assert webhooks[0]["name"] == "List Test"

    def test_get_webhook(self, client, auth_headers):
        """Test getting a specific webhook."""
        # Create a webhook first
        webhook_data = {
            "name": "Get Test",
            "url": "https://example.com/webhook",
            "events": ["edition.created"]
        }
        create_response = client.post("/api/webhooks", json=webhook_data, headers=auth_headers)
        webhook_id = create_response.json()["id"]

        response = client.get(f"/api/webhooks/{webhook_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test"

    def test_update_webhook(self, client, auth_headers):
        """Test updating a webhook."""
        # Create a webhook first
        webhook_data = {
            "name": "Update Test",
            "url": "https://example.com/webhook",
            "events": ["edition.created"]
        }
        create_response = client.post("/api/webhooks", json=webhook_data, headers=auth_headers)
        webhook_id = create_response.json()["id"]

        # Update webhook
        update_data = {
            "name": "Updated Name",
            "events": ["edition.created", "edition.processed"]
        }
        response = client.patch(
            f"/api/webhooks/{webhook_id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert len(response.json()["events"]) == 2

    def test_delete_webhook(self, client, auth_headers):
        """Test deleting a webhook."""
        # Create a webhook first
        webhook_data = {
            "name": "Delete Test",
            "url": "https://example.com/webhook",
            "events": ["edition.created"]
        }
        create_response = client.post("/api/webhooks", json=webhook_data, headers=auth_headers)
        webhook_id = create_response.json()["id"]

        # Delete webhook
        response = client.delete(f"/api/webhooks/{webhook_id}", headers=auth_headers)
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        # Verify deletion
        get_response = client.get(f"/api/webhooks/{webhook_id}", headers=auth_headers)
        assert get_response.status_code == 404

    def test_regenerate_secret(self, client, auth_headers):
        """Test regenerating webhook secret."""
        # Create a webhook first
        webhook_data = {
            "name": "Secret Test",
            "url": "https://example.com/webhook",
            "events": ["edition.created"]
        }
        create_response = client.post("/api/webhooks", json=webhook_data, headers=auth_headers)
        webhook_id = create_response.json()["id"]
        old_secret = create_response.json()["secret"]

        # Regenerate secret
        response = client.post(
            f"/api/webhooks/{webhook_id}/regenerate-secret",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "secret" in response.json()
        assert response.json()["secret"] != old_secret


class TestWebhookService:
    """Tests for webhook service functionality."""

    def test_get_active_webhooks_for_event(self, test_user, db):
        """Test filtering webhooks by event type."""

        # Create webhooks with different events
        webhook1 = Webhook(
            user_id=test_user["id"],
            name="Webhook 1",
            url="https://example.com/1",
            events=["edition.created", "edition.processed"],
            is_active=True
        )
        webhook2 = Webhook(
            user_id=test_user["id"],
            name="Webhook 2",
            url="https://example.com/2",
            events=["edition.failed"],
            is_active=True
        )
        webhook3 = Webhook(
            user_id=test_user["id"],
            name="Webhook 3",
            url="https://example.com/3",
            events=["edition.created"],
            is_active=False  # Inactive
        )
        db.add_all([webhook1, webhook2, webhook3])
        db.commit()

        service = WebhookService(db)

        # Test filtering
        created_webhooks = service.get_active_webhooks_for_event("edition.created")
        assert len(created_webhooks) == 1  # Only webhook1, webhook3 is inactive

        failed_webhooks = service.get_active_webhooks_for_event("edition.failed")
        assert len(failed_webhooks) == 1

    def test_create_signature(self, test_user, db):
        """Test HMAC signature creation."""
        service = WebhookService(db)

        payload = '{"test": "data"}'
        secret = "test_secret"

        signature = service.create_signature(payload, secret)
        assert signature is not None
        assert len(signature) == 64  # SHA-256 hex digest

        # Same input should produce same signature
        signature2 = service.create_signature(payload, secret)
        assert signature == signature2

        # Different secret should produce different signature
        signature3 = service.create_signature(payload, "different_secret")
        assert signature != signature3


class TestWebhookAuth:
    """Tests for webhook authentication requirements."""

    def test_create_webhook_requires_auth(self, client):
        """Test that creating webhook requires authentication."""
        webhook_data = {
            "name": "Test",
            "url": "https://example.com/webhook",
            "events": ["edition.created"]
        }
        response = client.post("/api/webhooks", json=webhook_data)
        assert response.status_code == 401

    def test_list_webhooks_requires_auth(self, client):
        """Test that listing webhooks requires authentication."""
        response = client.get("/api/webhooks")
        assert response.status_code == 401

    def test_user_can_only_access_own_webhooks(self, client, test_user, db):
        """Test that users can only access their own webhooks."""
        # Remove auth override to allow testing with different users/tokens
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]

        # Create webhook as first user
        headers1 = {"Authorization": f"Bearer {test_user['token']}"}
        webhook_data = {
            "name": "User1 Webhook",
            "url": "https://example.com/webhook",
            "events": ["edition.created"]
        }
        create_response = client.post("/api/webhooks", json=webhook_data, headers=headers1)
        webhook_id = create_response.json()["id"]

        # Create second user
        user2 = User(
            email="user2@example.com",
            hashed_password=get_password_hash("testpassword"),
            full_name="User 2",
            role=UserRole.READER.value,
            is_active=True,
            is_verified=True
        )
        db.add(user2)
        db.commit()
        user2_id = user2.id

        token2 = create_access_token({"sub": str(user2_id)})
        headers2 = {"Authorization": f"Bearer {token2}"}

        # User 2 should not see User 1's webhook
        response = client.get(f"/api/webhooks/{webhook_id}", headers=headers2)
        assert response.status_code == 404
