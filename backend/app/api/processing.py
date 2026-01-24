from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_admin_user
from app.db.database import SessionLocal, get_db
from app.models import Edition, ExtractionRun
from app.schemas import EditionResponse, EditionStatus
from app.services.processing_service import create_processing_service

router = APIRouter()


def run_processing_task(edition_id: int):
    """
    Background task that creates its own database session.
    This is needed because FastAPI's request-scoped session closes after the request.
    """
    # Create a new database session for the background task
    db = SessionLocal()
    try:
        processing_service = create_processing_service()
        processing_service.process_edition(edition_id, db)
    finally:
        db.close()


@router.post("/{edition_id}/process", response_model=EditionResponse)
async def process_edition(
    edition_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(get_admin_user)
):
    """
    Start processing an edition in the background.
    """
    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        raise HTTPException(
            status_code=404,
            detail="Edition not found"
        )

    # Check if already processing
    if edition.status == EditionStatus.PROCESSING:
        raise HTTPException(
            status_code=400,
            detail="Edition is already being processed"
        )

    # Update status to processing immediately
    edition.status = EditionStatus.PROCESSING  # type: ignore
    edition.current_stage = "QUEUED"  # type: ignore
    edition.last_error = None  # type: ignore
    db.commit()
    db.refresh(edition)

    # Add background task with its own session
    background_tasks.add_task(run_processing_task, edition_id)

    return edition


@router.get("/{edition_id}/status")
async def get_processing_status(
    edition_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed processing status for an edition including extraction runs.
    """
    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        raise HTTPException(
            status_code=404,
            detail="Edition not found"
        )

    # Get recent extraction runs
    extraction_runs = db.query(ExtractionRun).filter(
        ExtractionRun.edition_id == edition_id
    ).order_by(ExtractionRun.started_at.desc()).limit(5).all()

    return {
        "edition": {
            "id": edition.id,
            "status": edition.status,
            "last_error": edition.last_error,
            "processed_at": edition.processed_at,
            "total_pages": edition.total_pages,
            "processed_pages": edition.processed_pages,
            "current_stage": edition.current_stage,
            "archive_status": edition.archive_status,
            "archived_at": edition.archived_at,
        },
        "extraction_runs": [
            {
                "id": run.id,
                "version": run.version,
                "success": run.success,
                "status": run.status,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "completed_at": run.completed_at,
                "log_path": run.log_path,
                "stats": run.stats_json,
                "error_message": run.error_message,
            }
            for run in extraction_runs
        ]
    }
