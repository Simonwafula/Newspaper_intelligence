from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Edition, ExtractionRun
from app.schemas import EditionResponse
from app.services.processing_service import create_processing_service

router = APIRouter()


@router.post("/{edition_id}/process", response_model=EditionResponse)
async def process_edition(
    edition_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
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

    # Add background task to process the edition
    processing_service = create_processing_service()
    background_tasks.add_task(processing_service.process_edition, edition_id, db)

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
            "error_message": edition.error_message,
            "processed_at": edition.processed_at,
            "num_pages": edition.num_pages
        },
        "extraction_runs": [
            {
                "id": run.id,
                "version": run.version,
                "success": run.success,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "log_path": run.log_path,
                "stats": run.stats_json
            }
            for run in extraction_runs
        ]
    }
