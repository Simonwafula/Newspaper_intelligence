from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Edition
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
