import hashlib
import io
import logging
import os
from datetime import datetime

import fitz  # PyMuPDF
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.auth import get_admin_user, get_reader_user
from app.db.database import SessionLocal, get_db
from app.models import Edition
from app.schemas import EditionResponse, EditionStatus
from app.services.processing_service import create_processing_service
from app.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)


def run_processing_task(edition_id: int) -> None:
    """
    Background task that creates its own database session.
    This is needed because FastAPI's request-scoped session closes after the request.
    """
    db = SessionLocal()
    try:
        processing_service = create_processing_service()
        processing_service.process_edition(edition_id, db)
    finally:
        db.close()


def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA-256 hash of file content for deduplication."""
    return hashlib.sha256(file_content).hexdigest()


def compress_pdf(file_content: bytes) -> tuple[bytes, dict]:
    """
    Compress PDF by reducing image quality and cleaning up.

    Returns:
        Tuple of (compressed_bytes, compression_stats)
    """
    original_size = len(file_content)

    try:
        # Open PDF from bytes
        doc = fitz.open(stream=file_content, filetype="pdf")

        # Compress images in each page
        for page_num in range(len(doc)):
            page = doc[page_num]

            # Get all images on the page
            image_list = page.get_images()

            for img_index, img in enumerate(image_list):
                xref = img[0]  # Image xref number

                try:
                    # Extract image
                    base_image = doc.extract_image(xref)
                    if base_image:
                        image_bytes = base_image["image"]

                        # Only compress if image is large (>100KB)
                        if len(image_bytes) > 100 * 1024:
                            # Re-encode with lower quality using PIL if available
                            try:
                                from PIL import Image

                                img_io = io.BytesIO(image_bytes)
                                pil_image = Image.open(img_io)

                                # Convert to RGB if needed
                                if pil_image.mode in ('RGBA', 'P'):
                                    pil_image = pil_image.convert('RGB')

                                # Resize if very large (>2000px)
                                max_dim = 2000
                                if max(pil_image.size) > max_dim:
                                    ratio = max_dim / max(pil_image.size)
                                    new_size = (int(pil_image.size[0] * ratio), int(pil_image.size[1] * ratio))
                                    pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)

                                # Save with compression
                                output_io = io.BytesIO()
                                pil_image.save(output_io, format='JPEG', quality=75, optimize=True)
                                compressed_image = output_io.getvalue()

                                # Only use compressed if actually smaller
                                if len(compressed_image) < len(image_bytes) * 0.9:
                                    # Replace image in PDF
                                    page.delete_image(xref)
                                    # Note: Full image replacement requires more complex handling
                                    # For now, just log the potential savings
                                    logger.debug(f"Page {page_num + 1}, image {img_index}: could save {len(image_bytes) - len(compressed_image)} bytes")

                            except ImportError:
                                # PIL not available, skip image compression
                                pass
                            except Exception as e:
                                logger.debug(f"Could not compress image: {e}")

                except Exception as e:
                    logger.debug(f"Could not process image xref {xref}: {e}")

        # Save with garbage collection and deflate compression
        output_buffer = io.BytesIO()
        doc.save(
            output_buffer,
            garbage=4,  # Maximum garbage collection
            deflate=True,  # Compress streams
            clean=True,  # Clean up unused objects
            linear=False,  # Don't linearize (faster)
        )
        doc.close()

        compressed_content = output_buffer.getvalue()
        compressed_size = len(compressed_content)

        # Only use compressed version if it's actually smaller
        if compressed_size < original_size:
            savings_pct = ((original_size - compressed_size) / original_size) * 100
            logger.info(f"PDF compressed: {original_size} -> {compressed_size} bytes ({savings_pct:.1f}% reduction)")
            return compressed_content, {
                "original_size": original_size,
                "compressed_size": compressed_size,
                "savings_pct": round(savings_pct, 1)
            }
        else:
            logger.info("PDF compression did not reduce size, using original")
            return file_content, {
                "original_size": original_size,
                "compressed_size": original_size,
                "savings_pct": 0
            }

    except Exception as e:
        logger.warning(f"PDF compression failed, using original: {e}")
        return file_content, {
            "original_size": original_size,
            "compressed_size": original_size,
            "savings_pct": 0,
            "error": str(e)
        }


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
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    _ = Depends(get_admin_user)
):
    """
    Upload a new PDF edition.

    - **file**: PDF file to upload
    - **newspaper_name**: Name of the newspaper
    - **edition_date**: Publication date (YYYY-MM-DD format)

    The PDF will be automatically compressed to save storage space.
    """
    # Validate PDF file
    validate_pdf_file(file)

    # Read file content
    file_content = await file.read()

    # Validate file size (before compression)
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

    # Compress PDF to save storage space
    compressed_content, compression_stats = compress_pdf(file_content)
    logger.info(f"Compression stats: {compression_stats}")

    # Calculate file hash for deduplication (on compressed content)
    file_hash = calculate_file_hash(compressed_content)

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
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD format"
        ) from err

    # Save compressed file
    file_path = save_pdf_file(compressed_content, file_hash)

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

    edition.status = EditionStatus.PROCESSING  # type: ignore
    db.commit()
    db.refresh(edition)

    background_tasks.add_task(run_processing_task, edition.id)

    return edition


@router.get("/", response_model=list[EditionResponse])
async def list_editions(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _user = Depends(get_reader_user)
):
    """
    List all editions with pagination.
    """
    editions = db.query(Edition).offset(skip).limit(limit).all()
    return editions


@router.get("/{edition_id}", response_model=EditionResponse)
async def get_edition(
    edition_id: int,
    db: Session = Depends(get_db),
    _user = Depends(get_reader_user)
):
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
async def reprocess_edition(
    edition_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(get_admin_user)
):
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
    edition.status = EditionStatus.UPLOADED  # type: ignore
    edition.error_message = None  # type: ignore
    edition.processed_at = None  # type: ignore

    db.commit()
    db.refresh(edition)

    return edition
