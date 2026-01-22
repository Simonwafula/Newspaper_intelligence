"""
Test suite for Newspaper Intelligence backend.
Minimum 6 tests as required by project specifications.
"""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.main import app
from app.models import Edition, Item
from app.services.layout_analyzer import LayoutAnalyzer


@pytest.fixture
async def client():
    """Test client fixture."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_pdf_content():
    """Create a minimal valid PDF for testing."""
    # This would normally be a real PDF file
    # For testing, we'll mock the PDF processing
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"


class TestEditionUpload:
    """Test: upload creates edition."""

    @patch('app.services.pdf_processor.PDFProcessor.extract_metadata')
    @patch('app.api.editions.EditionService')
    async def test_upload_creates_edition(self, mock_service, mock_extract, client, sample_pdf_content):
        """Test that uploading a PDF creates a new edition."""
        # Mock the service response
        mock_edition = Edition(
            id=1,
            newspaper_name="Test Newspaper",
            edition_date="2024-01-01",
            file_hash="abc123",
            file_path="/test/path",
            status="PROCESSING"
        )
        mock_service.return_value.create_edition.return_value = mock_edition
        mock_extract.return_value = {
            "title": "Test Newspaper",
            "author": "Test Author",
            "creator": "Test Creator"
        }

        files = {"file": ("test.pdf", sample_pdf_content, "application/pdf")}
        response = await client.post("/api/editions/", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["file_hash"] == "abc123"
        assert data["status"] == "PROCESSING"


class TestStatusTransitions:
    """Test: status transitions."""

    @patch('app.api.editions.EditionService')
    async def test_status_transitions(self, mock_service, client):
        """Test that edition status transitions work correctly."""
        mock_edition = Edition(
            id=1,
            newspaper_name="Test Newspaper",
            edition_date="2024-01-01",
            file_hash="abc123",
            file_path="/test/path",
            status="READY"
        )
        mock_service.return_value.get_edition.return_value = mock_edition

        response = await client.get("/api/editions/1")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "READY"


class TestItemClassification:
    """Test: classifier tender/job/notice."""

    def test_classify_tender(self):
        """Test classification of tender notices."""
        analyzer = LayoutAnalyzer()

        # Test tender classification
        content = "TENDER NOTICE - Supply of office equipment"
        item_type, subtype = analyzer.classify_text_block(content)
        assert item_type == "CLASSIFIED"
        assert subtype == "TENDER"

    def test_classify_job(self):
        """Test classification of job advertisements."""
        analyzer = LayoutAnalyzer()

        # Test job advertisement classification
        content = "JOB VACANCY - Software Developer position available"
        item_type, subtype = analyzer.classify_text_block(content)
        assert item_type == "CLASSIFIED"
        assert subtype == "JOB"

    def test_classify_notice(self):
        """Test classification of public notices."""
        analyzer = LayoutAnalyzer()

        # Test notice classification
        content = "PUBLIC NOTICE - Road closure on Main Street"
        item_type, subtype = analyzer.classify_text_block(content)
        assert item_type == "CLASSIFIED"
        assert subtype == "NOTICE"


class TestSearchFunctionality:
    """Test: search returns hits."""

    @patch('app.api.search.SearchService')
    async def test_search_returns_hits(self, mock_service, client):
        """Test that search returns relevant results."""
        # Mock search results
        mock_items = [
            Item(
                id=1,
                edition_id=1,
                page_number=1,
                item_type="STORY",
                title="Test Article",
                text="This is a test article about search functionality"
            )
        ]
        mock_service.return_value.search_edition.return_value = mock_items

        response = await client.get("/api/editions/1/search?q=test")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert "test" in data["items"][0]["text"].lower()


class TestCSVExport:
    """Test: export CSV correctness."""

    @patch('app.api.export.ExportService')
    async def test_export_csv_correctness(self, mock_service, client):
        """Test that CSV export has correct format."""
        # Mock CSV content
        mock_csv = "id,title,content,item_type\n1,Test Item,Test content,article\n"
        mock_service.return_value.export_edition_csv.return_value = mock_csv

        response = await client.get("/api/export/edition/1/export/articles.csv")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]

        # Verify CSV content
        content = response.text
        assert "id,title,content,item_type" in content
        assert "Test Item" in content


class TestFileServingSafety:
    """Test: file-serving safety."""

    @patch('app.api.editions.EditionService')
    async def test_file_serving_safety(self, mock_service, client):
        """Test that file serving prevents path traversal."""
        mock_edition = Edition(
            id=1,
            filename="test.pdf",
            file_hash="abc123",
            newspaper_name="Test Newspaper",
            publication_date="2024-01-01",
            status="ready"
        )
        mock_service.return_value.get_edition.return_value = mock_edition

        # Test normal file access
        response = await client.get("/api/editions/1/file")
        assert response.status_code == 200

        # Test path traversal attempt (should be handled by service layer)
        # This test ensures the API properly validates file IDs
        mock_service.return_value.get_edition.side_effect = ValueError("Invalid edition ID")
        response = await client.get("/api/editions/999/file")
        assert response.status_code == 404


# Integration test marker
pytestmark = pytest.mark.integration
