import logging
import os
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Edition, ExtractionRun, Item, Page
from app.schemas import EditionStatus
from app.services.layout_analyzer import create_layout_analyzer
from app.services.ocr_service import create_ocr_service
from app.services.pdf_processor import create_pdf_processor
from app.settings import settings

logger = logging.getLogger(__name__)


class ProcessingService:
    """Main service for processing PDF editions."""

    def __init__(self):
        self.pdf_processor = create_pdf_processor(settings.min_chars_for_native_text)
        self.ocr_service = create_ocr_service(settings.ocr_languages) if settings.ocr_enabled else None
        self.layout_analyzer = create_layout_analyzer()

    def process_edition(self, edition_id: int, db: Session) -> bool:
        """
        Process a PDF edition: extract text, OCR if needed, analyze layout, extract items.

        Args:
            edition_id: ID of the edition to process
            db: Database session

        Returns:
            True if processing succeeded, False otherwise
        """
        edition = db.query(Edition).filter(Edition.id == edition_id).first()
        if not edition:
            logger.error(f"Edition {edition_id} not found")
            return False

        # Create extraction run record
        extraction_run = ExtractionRun(
            edition_id=edition_id,
            version="1.0",
            success=False
        )
        db.add(extraction_run)
        db.commit()
        db.refresh(extraction_run)

        try:
            # Update status to processing
            edition.status = EditionStatus.PROCESSING  # type: ignore
            edition.error_message = None  # type: ignore
            db.commit()

            logger.info(f"Starting processing for edition {edition_id}: {edition.newspaper_name}")

            # Get page count
            num_pages = self.pdf_processor.get_page_count(edition.file_path)
            edition.num_pages = num_pages
            db.commit()

            # Process each page
            total_items = 0
            pages_with_ocr = 0

            for page_num in range(num_pages):
                logger.info(f"Processing page {page_num + 1}/{num_pages}")

                # Extract text from page
                pages_data = self.pdf_processor.extract_all_pages(edition.file_path)
                if page_num >= len(pages_data):
                    logger.warning(f"Page {page_num + 1} not found in extracted data")
                    continue

                page_data = pages_data[page_num]

                # Create page record
                page = Page(
                    edition_id=edition_id,
                    page_number=page_num + 1,
                    extracted_text=page_data['extracted_text'],
                    bbox_json={'text_blocks': page_data.get('text_blocks', [])}
                )
                db.add(page)
                db.commit()
                db.refresh(page)

                # OCR if needed
                if page_data['needs_ocr'] and self.ocr_service and self.ocr_service.is_available():
                    try:
                        logger.info(f"Running OCR on page {page_num + 1}")

                        # Get page image
                        image_bytes = self.pdf_processor.get_page_image(edition.file_path, page_num)

                        # Save page image for reference
                        pages_dir = os.path.join(settings.storage_path, "pages")
                        os.makedirs(pages_dir, exist_ok=True)
                        image_path = os.path.join(pages_dir, f"{edition_id}_{page_num + 1}.png")

                        with open(image_path, 'wb') as f:
                            f.write(image_bytes)

                        page.image_path = image_path

                        # Extract text with OCR
                        ocr_result = self.ocr_service.extract_text_with_boxes(image_bytes)
                        page.extracted_text = ocr_result['text']

                        # Update page data with OCR results
                        page_data['extracted_text'] = ocr_result['text']
                        page_data['text_blocks'].extend(ocr_result['text_blocks'])
                        page.bbox_json = {'text_blocks': page_data['text_blocks']}

                        pages_with_ocr += 1

                        logger.info(f"OCR completed for page {page_num + 1}")

                    except Exception as e:
                        logger.error(f"OCR failed for page {page_num + 1}: {e}")
                        # Continue with native text extraction

                # Analyze layout and extract items
                try:
                    page_data = self.layout_analyzer.analyze_page(page_data)

                    # Save extracted items
                    for item_data in page_data.get('extracted_items', []):
                        item = Item(
                            edition_id=edition_id,
                            page_id=page.id,
                            page_number=page_num + 1,
                            item_type=item_data['item_type'],
                            subtype=item_data.get('subtype'),
                            title=item_data.get('title'),
                            text=item_data.get('text'),
                            bbox_json=item_data.get('bbox_json')
                        )
                        db.add(item)
                        total_items += 1

                    db.commit()

                except Exception as e:
                    logger.error(f"Layout analysis failed for page {page_num + 1}: {e}")
                    # Continue processing other pages

            # Update edition status
            edition.status = EditionStatus.READY  # type: ignore
            edition.processed_at = datetime.utcnow()  # type: ignore

            # Update extraction run
            extraction_run.success = True
            extraction_run.finished_at = datetime.utcnow()
            extraction_run.stats_json = {
                'total_pages': num_pages,
                'pages_with_ocr': pages_with_ocr,
                'total_items': total_items,
                'processing_time': (datetime.utcnow() - extraction_run.started_at).total_seconds()
            }

            db.commit()

            logger.info(f"Successfully processed edition {edition_id}: {num_pages} pages, {total_items} items extracted")
            return True

        except Exception as e:
            logger.error(f"Processing failed for edition {edition_id}: {e}")

            # Update edition status
            edition.status = EditionStatus.FAILED  # type: ignore
            edition.error_message = str(e)  # type: ignore

            # Update extraction run
            extraction_run.success = False
            extraction_run.finished_at = datetime.utcnow()

            db.commit()
            return False


def create_processing_service() -> ProcessingService:
    """Factory function to create ProcessingService instance."""
    return ProcessingService()
