import os
import hashlib
import shutil
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Edition, Page, Item, ExtractionRun
from app.schemas import EditionCreate, EditionResponse, EditionStatus
from app.settings import settings
from typing import Optional

router = APIRouter()


def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA-256 hash of file content for deduplication."""
    return hashlib.sha256(file_content).hexdigest()


def validate_pdf_file(file: UploadFile) -> None:
    """Validate that the uploaded file is a PDF."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Check file content type
    if file.content_type and not file.content_type == 'application/pdf':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content type must be application/pdf"
        )


def save_pdf_file(file_content: bytes, file_hash: str) -> str:
    """Save PDF file to storage and return the file path."""
    editions_dir = os.path.join(settings.storage_path, "editions")
    os.makedirs(editions_dir, exist_ok=True)
    
    file_path = os.path.join(editions_dir, f"{file_hash}.pdf")
    
    # Check if file already exists (shouldn't happen due to deduplication)
    if os.path.exists(file_path):
        return file_path
    
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    return file_path


@router.post("/", response_model=EditionResponse)
async def create_edition(
    file: UploadFile = File(...),
    newspaper_name: str = Form(...),
    edition_date: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Upload a new PDF edition.
    
    - **file**: PDF file to upload
    - **newspaper_name**: Name of the newspaper
    - **edition_date**: Publication date (YYYY-MM-DD format)
    """
    # Validate PDF file
    validate_pdf_file(file)
    
    # Read file content
    file_content = await file.read()
    
    # Validate file size
    max_size = settings.max_pdf_size.upper().replace('MB', '')
    try:
        max_size_bytes = int(max_size) * 1024 * 1024
    except ValueError:
        max_size_bytes = 50 * 1024 * 1024  # Default 50MB
    
    if len(file_content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {settings.max_pdf_size}"
        )
    
    # Calculate file hash for deduplication
    file_hash = calculate_file_hash(file_content)
    
    # Check for duplicate edition
    existing_edition = db.query(Edition).filter(Edition.file_hash == file_hash).first()
    if existing_edition:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An edition with this PDF already exists"
        )
    
    # Parse edition date
    try:
        parsed_date = datetime.fromisoformat(edition_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD format"
        )
    
    # Save file
    file_path = save_pdf_file(file_content, file_hash)
    
    # Create edition record
    edition = Edition(
        newspaper_name=newspaper_name,
        edition_date=parsed_date,
        file_hash=file_hash,
        file_path=file_path,
        status=EditionStatus.UPLOADED,
        num_pages=0  # Will be updated during processing
    )
    
    db.add(edition)
    db.commit()
    db.refresh(edition)
    
    return edition


@router.get("/", response_model=List[EditionResponse])
async def list_editions(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List all editions with pagination.
    """
    editions = db.query(Edition).offset(skip).limit(limit).all()
    return editions


@router.get("/{edition_id}", response_model=EditionResponse)
async def get_edition(edition_id: int, db: Session = Depends(get_db)):
    """
    Get a specific edition by ID.
    """
    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Edition not found"
        )
    return edition


@router.post("/{edition_id}/reprocess", response_model=EditionResponse)
async def reprocess_edition(edition_id: int, db: Session = Depends(get_db)):
    """
    Reprocess an edition (re-run text extraction and analysis).
    """
    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Edition not found"
        )
    
    # Reset status to trigger reprocessing
    edition.status = EditionStatus.UPLOADED.value
    edition.error_message = None  # type: ignore
    edition.processed_at = None  # type: ignore
    
    db.commit()
    db.refresh(edition)
    
    return edition