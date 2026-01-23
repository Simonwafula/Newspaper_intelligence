import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Edition, ExtractionRun, Item, Page, ItemCategory
from app.schemas import EditionStatus
from app.services.category_classifier import CategoryClassifier
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

            pages_data = self.pdf_processor.extract_all_pages(edition.file_path)

            stats = {
                'total_pages': num_pages,
                'pages_processed': 0,
                'pages_with_ocr': 0,
                'total_items': 0
            }
            extraction_run.stats_json = dict(stats)
            db.commit()

            total_items = 0
            pages_with_ocr = 0
            pages_processed = 0
            commit_interval = max(1, settings.processing_db_commit_interval)
            pending_commits = 0

            def process_page(page_num: int) -> dict | None:
                page_data = pages_data[page_num]
                page_data = dict(page_data)
                page_data['text_blocks'] = list(page_data.get('text_blocks', []))

                used_ocr = False
                image_path = None

                if page_data.get('needs_ocr') and self.ocr_service and self.ocr_service.is_available():
                    try:
                        logger.info(f"Running OCR on page {page_num + 1}")

                        image_bytes = self.pdf_processor.get_page_image(edition.file_path, page_num)

                        pages_dir = os.path.join(settings.storage_path, "pages")
                        os.makedirs(pages_dir, exist_ok=True)
                        image_path = os.path.join(pages_dir, f"{edition_id}_{page_num + 1}.png")

                        with open(image_path, 'wb') as f:
                            f.write(image_bytes)

                        ocr_result = self.ocr_service.extract_text_with_boxes(image_bytes)
                        page_data['extracted_text'] = ocr_result['text']
                        page_data['text_blocks'].extend(ocr_result['text_blocks'])
                        used_ocr = True

                        logger.info(f"OCR completed for page {page_num + 1}")

                    except Exception as e:
                        logger.error(f"OCR failed for page {page_num + 1}: {e}")

                try:
                    page_data = self.layout_analyzer.analyze_page(page_data)
                except Exception as e:
                    logger.error(f"Layout analysis failed for page {page_num + 1}: {e}")
                    page_data['extracted_items'] = []

                return {
                    'page_num': page_num,
                    'page_data': page_data,
                    'image_path': image_path,
                    'used_ocr': used_ocr,
                }

            def persist_page(result: dict | None) -> None:
                nonlocal total_items, pages_with_ocr, pages_processed, pending_commits

                pages_processed += 1

                if result is None:
                    stats['pages_processed'] = pages_processed
                    extraction_run.stats_json = dict(stats)
                else:
                    page_num = result['page_num']
                    page_data = result['page_data']

                    page = Page(
                        edition_id=edition_id,
                        page_number=page_num + 1,
                        extracted_text=page_data.get('extracted_text'),
                        bbox_json={'text_blocks': page_data.get('text_blocks', [])}
                    )
                    if result.get('image_path'):
                        page.image_path = result['image_path']

                    db.add(page)
                    db.flush()

                    extracted_items = page_data.get('extracted_items', [])
                    for item_data in extracted_items:
                        item = Item(
                            edition_id=edition_id,
                            page_id=page.id,
                            page_number=page_num + 1,
                            item_type=item_data['item_type'],
                            subtype=item_data.get('subtype'),
                            title=item_data.get('title'),
                            text=item_data.get('text'),
                            bbox_json=item_data.get('bbox_json'),
                            structured_data=item_data.get('structured_data'),
                            contact_info_json=item_data.get('contact_info_json'),
                            price_info_json=item_data.get('price_info_json'),
                            date_info_json=item_data.get('date_info_json'),
                            location_info_json=item_data.get('location_info_json'),
                            classification_details_json=item_data.get('classification_details_json')
                        )
                        db.add(item)
                        total_items += 1

                    if result.get('used_ocr'):
                        pages_with_ocr += 1

                    stats['pages_processed'] = pages_processed
                    stats['pages_with_ocr'] = pages_with_ocr
                    stats['total_items'] = total_items
                    extraction_run.stats_json = dict(stats)

                pending_commits += 1
                if pending_commits >= commit_interval or pages_processed == num_pages:
                    db.commit()
                    pending_commits = 0

            if num_pages > len(pages_data):
                logger.warning("PDF page count mismatch: extracted fewer pages than expected")

            max_workers = max(1, settings.processing_max_workers)
            max_pages = min(num_pages, len(pages_data))

            if max_workers > 1:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [executor.submit(process_page, page_num) for page_num in range(max_pages)]
                    for future in as_completed(futures):
                        try:
                            result = future.result()
                        except Exception as e:
                            logger.error(f"Page processing failed: {e}")
                            result = None
                        persist_page(result)
            else:
                for page_num in range(max_pages):
                    logger.info(f"Processing page {page_num + 1}/{num_pages}")
                    try:
                        result = process_page(page_num)
                    except Exception as e:
                        logger.error(f"Page processing failed for page {page_num + 1}: {e}")
                        result = None
                    persist_page(result)

            # Update edition status
            edition.status = EditionStatus.READY  # type: ignore
            edition.processed_at = datetime.utcnow()  # type: ignore

            # Update extraction run
            extraction_run.success = True
            extraction_run.finished_at = datetime.utcnow()
            stats.update({
                'pages_processed': pages_processed,
                'pages_with_ocr': pages_with_ocr,
                'total_items': total_items,
                'processing_time': (datetime.utcnow() - extraction_run.started_at).total_seconds()
            })
            extraction_run.stats_json = dict(stats)

            # Run category classification on all extracted items
            try:
                logger.info("Running category classification...")
                category_classifier = CategoryClassifier(db)
                all_items = db.query(Item).filter(Item.edition_id == edition_id).all()
                
                if all_items:
                    classification_results = category_classifier.batch_classify_items(
                        all_items, confidence_threshold=30, clear_existing=True
                    )
                    classified_count = len(classification_results)
                    total_classifications = sum(len(classifications) for classifications in classification_results.values())
                    
                    logger.info(f"Classified {classified_count} items with {total_classifications} total classifications")
                    
                    # Update stats with classification info
                    stats.update({
                        'items_classified': classified_count,
                        'total_classifications': total_classifications
                    })
            except Exception as e:
                logger.error(f"Category classification failed: {e}")
                # Don't fail the entire processing if classification fails

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
