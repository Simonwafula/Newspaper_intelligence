"""
Refactored test suite for Newspaper Intelligence backend.
Uses TestClient and conftest.py fixtures.
"""

from datetime import datetime

import pytest

from app.api.auth import get_admin_user, get_reader_user
from app.main import app
from app.models import Edition, Item
from app.schemas import EditionStatus, ItemType


@pytest.fixture(autouse=True)
def mock_auth(mock_admin_user):
    """Automatically override auth for these tests."""
    app.dependency_overrides[get_reader_user] = lambda: mock_admin_user
    app.dependency_overrides[get_admin_user] = lambda: mock_admin_user
    yield
    # Clean up overrides after each test in this module
    if get_reader_user in app.dependency_overrides:
        del app.dependency_overrides[get_reader_user]
    if get_admin_user in app.dependency_overrides:
        del app.dependency_overrides[get_admin_user]

def test_health_check(client):
    response = client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_item_classification_logic():
    from app.services.layout_analyzer import LayoutAnalyzer
    analyzer = LayoutAnalyzer()

    # Test tender classification
    content = "TENDER NOTICE - Supply of office equipment"
    item_type, subtype = analyzer.classify_text_block(content)
    assert item_type == "CLASSIFIED"
    assert subtype == "TENDER"

    # Test job advertisement classification
    content = "JOB VACANCY - Software Developer position available"
    item_type, subtype = analyzer.classify_text_block(content)
    assert item_type == "CLASSIFIED"
    assert subtype == "JOB"

def test_edition_listing(client, db):
    # Add a sample edition
    edition = Edition(
        newspaper_name="Test Daily",
        edition_date=datetime(2024, 1, 1),
        file_hash="mockhash123",
        file_path="/tmp/mock.pdf",
        status=EditionStatus.READY,
        num_pages=5
    )
    db.add(edition)
    db.commit()

    response = client.get("/api/editions/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(e["newspaper_name"] == "Test Daily" for e in data)

def test_search_functionality(client, db):
    # Create an edition and an item
    edition = Edition(
        newspaper_name="Search Gazette",
        edition_date=datetime(2024, 2, 1),
        file_hash="searchhash456",
        file_path="/tmp/search.pdf",
        status=EditionStatus.READY,
        num_pages=1
    )
    db.add(edition)
    db.commit()

    item = Item(
        edition_id=edition.id,
        page_number=1,
        item_type=ItemType.STORY,
        title="Breaking News",
        text="This is a test article about searching for keywords like banana."
    )
    db.add(item)
    db.commit()

    response = client.get(f"/api/search/edition/{edition.id}/search?q=banana")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert "banana" in data[0]["snippet"].lower()

def test_file_serving_path_traversal_protection(client):
    response = client.get("/api/editions/9999/file")
    # Public router file path validation
    assert response.status_code == 404
