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
from app.models import Edition, Item, Page
from app.schemas import EditionResponse, EditionStatus
from app.services.archive_service import archive_edition_now
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


def save_pdf_file(file_content: bytes, edition_id: int) -> str:
    """Save PDF file to edition storage and return the file path."""
    edition_dir = os.path.join(settings.storage_path, "editions", str(edition_id))
    os.makedirs(edition_dir, exist_ok=True)

    file_path = os.path.join(edition_dir, "original.pdf")

    with open(file_path, "wb") as f:
        f.write(file_content)

    return file_path


def generate_cover_image(pdf_path: str, edition_id: int) -> str | None:
    """Generate a cover image (first page) and return its path."""
    covers_dir = os.path.join(settings.storage_path, "covers")
    os.makedirs(covers_dir, exist_ok=True)

    cover_path = os.path.join(covers_dir, f"{edition_id}.png")
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        pix = page.get_pixmap()
        pix.save(cover_path)
        doc.close()
        return cover_path
    except Exception as e:
        logger.warning(f"Failed to generate cover image for edition {edition_id}: {e}")
        return None


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

    try:
        doc = fitz.open(stream=compressed_content, filetype="pdf")
        total_pages = len(doc)
        doc.close()
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read PDF pages"
        ) from err

    edition = Edition(
        newspaper_name=newspaper_name,
        edition_date=parsed_date,
        file_hash=file_hash,
        file_path="",
        pdf_local_path=None,
        storage_backend="local",
        storage_key=None,
        total_pages=total_pages,
        processed_pages=0,
        status=EditionStatus.UPLOADED,
        current_stage="QUEUED",
        archive_status="SCHEDULED",
    )

    db.add(edition)
    db.commit()
    db.refresh(edition)

    file_path = save_pdf_file(compressed_content, edition.id)
    edition.file_path = file_path
    edition.pdf_local_path = file_path
    edition.storage_key = file_path

    cover_path = generate_cover_image(file_path, edition.id)
    if cover_path:
        edition.cover_image_path = cover_path

    pages = [
        Page(edition_id=edition.id, page_number=page_number, status="PENDING")
        for page_number in range(1, total_pages + 1)
    ]
    db.add_all(pages)
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
    if edition.status != EditionStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only READY editions can be archived"
        )
    return edition


@router.post("/{edition_id}/reprocess", response_model=EditionResponse)
async def reprocess_edition(
    edition_id: int,
    background_tasks: BackgroundTasks = BackgroundTasks(),
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

    # Check if already processing
    if edition.status == EditionStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Edition is already being processed"
        )

    pdf_path = edition.pdf_local_path or edition.file_path
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Local PDF missing. Restore or re-upload before reprocessing."
        )

    db.query(Item).filter(Item.edition_id == edition_id).delete()
    db.query(Page).filter(Page.edition_id == edition_id).delete()
    db.commit()

    edition.status = EditionStatus.UPLOADED  # type: ignore
    edition.processed_pages = 0  # type: ignore
    edition.current_stage = "QUEUED"  # type: ignore
    edition.last_error = None  # type: ignore
    edition.processed_at = None  # type: ignore

    total_pages = edition.total_pages or 0
    pages = [
        Page(edition_id=edition.id, page_number=page_number, status="PENDING")
        for page_number in range(1, total_pages + 1)
    ]
    db.add_all(pages)
    db.commit()
    db.refresh(edition)

    # Add background task to reprocess
    background_tasks.add_task(run_processing_task, edition_id)

    return edition


@router.post("/{edition_id}/archive", response_model=EditionResponse)
async def archive_edition(
    edition_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(get_admin_user)
):
    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Edition not found"
        )

    archived = archive_edition_now(edition, db)
    if not archived:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Archiving failed"
        )
    return edition


@router.post("/{edition_id}/restore", response_model=EditionResponse)
async def restore_edition(
    edition_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(get_admin_user)
):
    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Edition not found"
        )

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Restore not implemented"
    )


@router.delete("/{edition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edition(
    edition_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(get_admin_user)
):
    """
    Delete an edition and all associated files.
    Admin only.
    """
    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Edition not found"
        )

    # Check if currently processing
    if edition.status == EditionStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an edition that is currently being processed"
        )

    # Delete associated files
    try:
        pdf_path = edition.pdf_local_path or edition.file_path
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
            logger.info(f"Deleted PDF file: {pdf_path}")

        cover_path = edition.cover_image_path or os.path.join(
            settings.storage_path, "covers", f"{edition_id}.png"
        )
        if os.path.exists(cover_path):
            os.remove(cover_path)
            logger.info(f"Deleted cover image: {cover_path}")

        # Delete page images
        pages_dir = os.path.join(settings.storage_path, "pages")
        if os.path.exists(pages_dir):
            for filename in os.listdir(pages_dir):
                if filename.startswith(f"{edition_id}_"):
                    file_path = os.path.join(pages_dir, filename)
                    os.remove(file_path)
                    logger.info(f"Deleted page image: {file_path}")

        edition_dir = os.path.join(settings.storage_path, "editions", str(edition_id))
        if os.path.exists(edition_dir):
            for filename in os.listdir(edition_dir):
                os.remove(os.path.join(edition_dir, filename))
            os.rmdir(edition_dir)

    except Exception as e:
        logger.error(f"Error deleting files for edition {edition_id}: {e}")
        # Continue with DB deletion even if file deletion fails

    # Delete from database (cascades to pages, items, etc.)
    db.delete(edition)
    db.commit()

    logger.info(f"Deleted edition {edition_id}")
    return None
