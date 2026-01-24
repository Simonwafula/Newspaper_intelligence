from datetime import datetime
from pathlib import Path

import fitz

from app.models import Edition, Page
from app.services.processing_service import ProcessingService
from app.settings import settings


def _create_pdf(path: Path, pages: int) -> None:
    doc = fitz.open()
    for page_index in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {page_index + 1}")
    doc.save(str(path))
    doc.close()


def test_processing_updates_progress(db, tmp_path, monkeypatch):
    pdf_path = tmp_path / "edition.pdf"
    _create_pdf(pdf_path, pages=2)

    monkeypatch.setattr(settings, "ocr_enabled", False)

    edition = Edition(
        newspaper_name="Progress Times",
        edition_date=datetime(2024, 1, 1),
        file_hash="hash_progress",
        file_path=str(pdf_path),
        pdf_local_path=str(pdf_path),
        storage_backend="local",
        storage_key=str(pdf_path),
        total_pages=0,
        processed_pages=0,
        status="UPLOADED",
        current_stage="QUEUED",
        archive_status="SCHEDULED",
    )
    db.add(edition)
    db.commit()
    db.refresh(edition)
    assert edition.status == "UPLOADED"

    pages = [
        Page(edition_id=edition.id, page_number=page_number, status="PENDING")
        for page_number in range(1, 3)
    ]
    db.add_all(pages)
    db.commit()

    service = ProcessingService()
    assert service.process_edition(edition.id, db) is True

    db.refresh(edition)
    assert edition.status == "READY"
    assert edition.total_pages == 2
    assert edition.processed_pages == 2
    assert edition.current_stage == "DONE"
    assert db.query(Page).filter(Page.edition_id == edition.id).count() == 2


def test_create_edition_creates_pages(client, db, mock_admin_user, monkeypatch, tmp_path):
    from app.api import editions as editions_api
    from app.api.auth import get_admin_user
    from app.main import app

    app.dependency_overrides[get_admin_user] = lambda: mock_admin_user
    monkeypatch.setattr(editions_api, "run_processing_task", lambda edition_id: None)

    pdf_path = tmp_path / "upload.pdf"
    _create_pdf(pdf_path, pages=3)
    pdf_bytes = pdf_path.read_bytes()

    response = client.post(
        "/api/editions/",
        data={"newspaper_name": "Upload Gazette", "edition_date": "2024-01-15"},
        files={"file": ("upload.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    edition_id = response.json()["id"]

    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    assert edition is not None
    assert edition.total_pages == 3

    page_count = db.query(Page).filter(Page.edition_id == edition_id).count()
    assert page_count == 3

    app.dependency_overrides.pop(get_admin_user, None)
