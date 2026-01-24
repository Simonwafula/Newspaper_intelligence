from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.models import Edition
from app.services import archive_service
from app.settings import settings


class _FakeDriveClient:
    def __init__(self, file_id: str = "drive_file_id"):
        self.file_id = file_id

    def upload_file(self, local_path: str, filename: str | None = None):
        return _UploadResult(file_id=self.file_id, size=123)


class _UploadResult:
    def __init__(self, file_id: str, size: int):
        self.file_id = file_id
        self.size = size


def _create_pdf(path: Path) -> None:
    path.write_bytes(b"%PDF-1.4\n%EOF\n")


def test_archive_due_editions(db, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "gdrive_enabled", True)
    monkeypatch.setattr(archive_service, "_get_drive_client", lambda: _FakeDriveClient())

    old_pdf = tmp_path / "old.pdf"
    new_pdf = tmp_path / "new.pdf"
    _create_pdf(old_pdf)
    _create_pdf(new_pdf)

    old_edition = Edition(
        newspaper_name="Old Daily",
        edition_date=datetime(2024, 1, 1),
        file_hash="old_hash",
        file_path=str(old_pdf),
        pdf_local_path=str(old_pdf),
        storage_backend="local",
        storage_key=str(old_pdf),
        total_pages=1,
        processed_pages=1,
        status="READY",
        current_stage="DONE",
        archive_status="SCHEDULED",
        created_at=datetime.now(timezone.utc) - timedelta(days=6),
    )
    new_edition = Edition(
        newspaper_name="New Daily",
        edition_date=datetime(2024, 1, 2),
        file_hash="new_hash",
        file_path=str(new_pdf),
        pdf_local_path=str(new_pdf),
        storage_backend="local",
        storage_key=str(new_pdf),
        total_pages=1,
        processed_pages=1,
        status="READY",
        current_stage="DONE",
        archive_status="SCHEDULED",
        created_at=datetime.now(timezone.utc),
    )

    db.add_all([old_edition, new_edition])
    db.commit()

    archived_count = archive_service.archive_due_editions(db)
    assert archived_count == 1

    db.refresh(old_edition)
    db.refresh(new_edition)

    assert old_edition.archive_status == "ARCHIVED"
    assert old_edition.storage_backend == "gdrive"
    assert old_edition.storage_key == "drive_file_id"
    assert old_edition.pdf_local_path is None
    assert not Path(old_pdf).exists()

    assert new_edition.archive_status == "SCHEDULED"
    assert new_edition.storage_backend == "local"


def test_archive_skips_processing_editions(db, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "gdrive_enabled", True)
    monkeypatch.setattr(archive_service, "_get_drive_client", lambda: _FakeDriveClient())

    processing_pdf = tmp_path / "processing.pdf"
    _create_pdf(processing_pdf)

    edition = Edition(
        newspaper_name="Processing Daily",
        edition_date=datetime(2024, 1, 3),
        file_hash="processing_hash",
        file_path=str(processing_pdf),
        pdf_local_path=str(processing_pdf),
        storage_backend="local",
        storage_key=str(processing_pdf),
        total_pages=1,
        processed_pages=0,
        status="PROCESSING",
        current_stage="EXTRACT",
        archive_status="SCHEDULED",
        created_at=datetime.now(timezone.utc) - timedelta(days=6),
    )
    db.add(edition)
    db.commit()

    archived_count = archive_service.archive_due_editions(db)
    assert archived_count == 0

    db.refresh(edition)
    assert edition.archive_status == "SCHEDULED"
    assert Path(processing_pdf).exists()
