"""
Tests for external API endpoints with API key authentication.
"""

import pytest
from app.api.external import get_api_key_user
from app.main import app
from app.models import Edition, Item, User, UserAPIKey, UserRole
from app.schemas import ItemType
from app.utils.auth import get_password_hash


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test User",
        role=UserRole.ADMIN.value,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "user": user}


@pytest.fixture
def test_api_key(db, test_user):
    """Create a test API key and set up auth override."""
    import hashlib

    api_key = "test_key_123456789"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    api_key_record = UserAPIKey(
        user_id=test_user["id"],
        name="Test Key",
        key_hash=key_hash,
        key_prefix="test_key_1",
        is_active=True,
        rate_limit_per_hour=1000,
        rate_limit_per_day=10000
    )
    db.add(api_key_record)
    db.commit()

    # Override get_api_key_user to return the test user
    async def override_get_api_key_user():
        return test_user["user"]
    
    app.dependency_overrides[get_api_key_user] = override_get_api_key_user
    yield api_key
    # Cleanup override
    if get_api_key_user in app.dependency_overrides:
        del app.dependency_overrides[get_api_key_user]


@pytest.fixture
def test_edition(db):
    """Create a test edition with items."""
    from datetime import datetime

    edition = Edition(
        newspaper_name="Test Newspaper",
        edition_date=datetime(2024, 1, 15),
        file_hash="test_hash_123",
        file_path="/test/path.pdf",
        num_pages=5,
        status="READY"
    )
    db.add(edition)
    db.commit()
    db.refresh(edition)

    # Add items
    item1 = Item(
        edition_id=edition.id,
        page_number=1,
        item_type=ItemType.STORY.value,
        title="Test Article",
        text="This is a test article about economics and business."
    )
    item2 = Item(
        edition_id=edition.id,
        page_number=2,
        item_type=ItemType.CLASSIFIED.value,
        subtype="JOB",
        title="Software Developer",
        text="We are looking for a software developer with 5 years experience."
    )
    db.add_all([item1, item2])
    db.commit()

    return edition.id


class TestExternalAPIAuthentication:
    """Tests for API key authentication."""

    def test_unauthorized_without_api_key(self, client):
        """Test that endpoints require API key."""
        response = client.get("/api/external/editions")
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_unauthorized_with_invalid_key(self, client):
        """Test that invalid API key is rejected."""
        response = client.get(
            "/api/external/editions",
            headers={"Authorization": "Bearer invalid_key"}
        )
        assert response.status_code == 401
        assert "Invalid or expired API key" in response.json()["detail"]

    def test_authorized_with_valid_key(self, client, test_api_key, test_edition):
        """Test that valid API key is accepted."""
        response = client.get(
            "/api/external/editions",
            headers={"Authorization": f"Bearer {test_api_key}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "editions" in data
        assert len(data["editions"]) >= 1


class TestExternalAPIEndpoints:
    """Tests for external API data endpoints."""

    def test_get_editions(self, client, test_api_key, test_edition):
        """Test listing editions via external API."""
        response = client.get(
            "/api/external/editions",
            headers={"Authorization": f"Bearer {test_api_key}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "editions" in data
        assert data["editions"][0]["newspaper_name"] == "Test Newspaper"

    def test_get_editions_with_filter(self, client, test_api_key, test_edition):
        """Test filtering editions by newspaper name."""
        response = client.get(
            "/api/external/editions?newspaper=Test",
            headers={"Authorization": f"Bearer {test_api_key}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["editions"]) >= 1

    def test_get_edition_items(self, client, test_api_key, test_edition):
        """Test getting items for an edition."""
        response = client.get(
            f"/api/external/editions/{test_edition}/items",
            headers={"Authorization": f"Bearer {test_api_key}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2
        assert data["edition_info"]["id"] == test_edition

    def test_get_edition_items_with_type_filter(self, client, test_api_key, test_edition):
        """Test filtering items by type."""
        response = client.get(
            f"/api/external/editions/{test_edition}/items?item_type=CLASSIFIED",
            headers={"Authorization": f"Bearer {test_api_key}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["item_type"] == "CLASSIFIED"

    def test_search_items(self, client, test_api_key, test_edition):
        """Test searching items via external API."""
        response = client.get(
            "/api/external/search?q=software",
            headers={"Authorization": f"Bearer {test_api_key}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1
        assert "software" in data["items"][0]["text"].lower()

    def test_get_api_stats(self, client, test_api_key, test_user):
        """Test getting API usage statistics."""
        response = client.get(
            "/api/external/stats",
            headers={"Authorization": f"Bearer {test_api_key}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "active_keys" in data
        assert "total_requests" in data

    def test_edition_not_found(self, client, test_api_key):
        """Test 404 for non-existent edition."""
        response = client.get(
            "/api/external/editions/99999/items",
            headers={"Authorization": f"Bearer {test_api_key}"}
        )
        assert response.status_code == 404


class TestAPIKeyManagement:
    """Tests for API key management endpoints."""

    def test_list_api_keys_requires_auth(self, client):
        """Test that listing keys requires JWT auth."""
        response = client.get("/api/external/keys")
        assert response.status_code == 401
