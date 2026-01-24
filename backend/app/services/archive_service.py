import os
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Edition
from app.services.gdrive_client import DriveClient
from app.settings import settings


def _get_drive_client() -> DriveClient:
    if not settings.gdrive_enabled:
        raise RuntimeError("Google Drive archiving disabled")
    if not settings.gdrive_service_account_file:
        raise RuntimeError("GDRIVE_SERVICE_ACCOUNT_FILE not set")

    return DriveClient(
        settings.gdrive_service_account_file,
        settings.gdrive_folder_id,
    )


def archive_edition_now(edition: Edition, db: Session) -> bool:
    if edition.storage_backend == "gdrive":
        return True

    pdf_path = edition.pdf_local_path or edition.file_path
    if not pdf_path or not os.path.exists(pdf_path):
        edition.archive_status = "ARCHIVE_FAILED"  # type: ignore
        edition.last_error = "Local PDF missing; cannot archive"  # type: ignore
        db.commit()
        return False

    try:
        edition.archive_status = "ARCHIVING"  # type: ignore
        db.commit()

        client = _get_drive_client()
        upload_result = client.upload_file(pdf_path)
        if upload_result.size is not None and upload_result.size <= 0:
            raise RuntimeError("Drive upload returned empty file")

        edition.storage_backend = "gdrive"  # type: ignore
        edition.storage_key = upload_result.file_id  # type: ignore
        edition.pdf_local_path = None  # type: ignore
        edition.archived_at = datetime.now(UTC)  # type: ignore
        edition.archive_status = "ARCHIVED"  # type: ignore
        edition.status = "ARCHIVED"  # type: ignore
        edition.last_error = None  # type: ignore

        os.remove(pdf_path)
        db.commit()
        return True
    except Exception as e:
        edition.archive_status = "ARCHIVE_FAILED"  # type: ignore
        edition.last_error = str(e)[:500]  # type: ignore
        db.commit()
        return False


def archive_due_editions(db: Session) -> int:
    if not settings.gdrive_enabled:
        return 0

    cutoff = datetime.now(UTC) - timedelta(days=settings.archive_after_days)
    editions = (
        db.query(Edition)
        .filter(Edition.archive_status.in_(["SCHEDULED", "ARCHIVE_FAILED"]))
        .filter(Edition.created_at <= cutoff)
        .filter(Edition.storage_backend == "local")
        .filter(Edition.status == "READY")
        .all()
    )

    archived_count = 0
    for edition in editions:
        if archive_edition_now(edition, db):
            archived_count += 1

    return archived_count
