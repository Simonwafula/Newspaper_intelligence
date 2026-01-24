import logging
import os
from datetime import UTC, datetime

import fitz
from sqlalchemy.orm import Session

from app.models import Edition, ExtractionRun, Item, Page
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
        Process a PDF edition page-by-page.

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

        pdf_path = edition.pdf_local_path or edition.file_path
        if not pdf_path or not os.path.exists(pdf_path):
            edition.status = EditionStatus.FAILED  # type: ignore
            edition.last_error = "Local PDF missing; cannot process"  # type: ignore
            db.commit()
            return False

        extraction_run = ExtractionRun(
            edition_id=edition_id,
            version="1.0",
            success=False,
            status="RUNNING",
        )
        db.add(extraction_run)
        db.commit()
        db.refresh(extraction_run)

        log_path = os.path.join(settings.processing_log_dir, f"edition_{edition_id}_run_{extraction_run.id}.log")
        extraction_run.log_path = log_path
        db.commit()

        def append_log(message: str) -> None:
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(message + "\n")

        try:
            edition.status = EditionStatus.PROCESSING  # type: ignore
            edition.current_stage = "QUEUED"  # type: ignore
            edition.last_error = None  # type: ignore
            db.commit()

            logger.info(f"Starting processing for edition {edition_id}: {edition.newspaper_name}")
            append_log(f"Processing started for edition {edition_id}")

            doc = fitz.open(pdf_path)
            total_pages = edition.total_pages or len(doc)
            if total_pages != len(doc):
                total_pages = len(doc)

            edition.total_pages = total_pages  # type: ignore
            edition.processed_pages = 0  # type: ignore
            db.commit()

            stats = {
                "total_pages": total_pages,
                "processed_pages": 0,
                "pages_with_ocr": 0,
                "total_items": 0,
            }
            extraction_run.stats_json = dict(stats)
            db.commit()

            total_items = 0
            pages_with_ocr = 0
            processed_pages = 0
            any_failed = False

            for page_index in range(total_pages):
                db.refresh(edition)
                if str(edition.status) == "CANCELLED":
                    append_log("Processing cancelled")
                    doc.close()
                    extraction_run.status = "FAILED"
                    extraction_run.error_message = "Cancelled"
                    extraction_run.completed_at = datetime.now(UTC)
                    db.commit()
                    return False

                page_number = page_index + 1
                page = db.query(Page).filter(Page.edition_id == edition_id, Page.page_number == page_number).first()
                if not page:
                    page = Page(edition_id=edition_id, page_number=page_number)
                    db.add(page)
                    db.flush()

                page.status = "PROCESSING"
                db.commit()

                try:
                    edition.current_stage = "EXTRACT"  # type: ignore
                    db.commit()

                    page_data = self.pdf_processor.get_page_data(doc, page_index)
                    used_ocr = False
                    image_path = None

                    if page_data.get("needs_ocr") and self.ocr_service and self.ocr_service.is_available():
                        edition.current_stage = "OCR"  # type: ignore
                        db.commit()

                        image_bytes = self.pdf_processor.get_page_image(
                            pdf_path, page_index, dpi=settings.ocr_image_dpi
                        )
                        pages_dir = os.path.join(settings.storage_path, "pages")
                        os.makedirs(pages_dir, exist_ok=True)
                        image_path = os.path.join(pages_dir, f"{edition_id}_{page_number}.png")
                        with open(image_path, "wb") as f:
                            f.write(image_bytes)

                        ocr_result = self.ocr_service.extract_text_with_boxes(image_bytes)
                        page_data["extracted_text"] = ocr_result["text"]
                        page_data["text_blocks"].extend(ocr_result["text_blocks"])
                        used_ocr = True

                    edition.current_stage = "LAYOUT"  # type: ignore
                    db.commit()

                    try:
                        page_data = self.layout_analyzer.analyze_page(page_data)
                    except Exception as e:
                        logger.error(f"Layout analysis failed for page {page_number}: {e}")
                        page_data["extracted_items"] = []

                    edition.current_stage = "INDEX"  # type: ignore
                    db.commit()

                    page.extracted_text = page_data.get("extracted_text")
                    page.bbox_json = {"text_blocks": page_data.get("text_blocks", [])}
                    page.char_count = len(page_data.get("extracted_text") or "")
                    page.ocr_used = used_ocr
                    if image_path:
                        page.image_path = image_path

                    extracted_items = page_data.get("extracted_items", [])
                    for item_data in extracted_items:
                        item = Item(
                            edition_id=edition_id,
                            page_id=page.id,
                            page_number=page_number,
                            item_type=item_data["item_type"],
                            subtype=item_data.get("subtype"),
                            title=item_data.get("title"),
                            text=item_data.get("text"),
                            bbox_json=item_data.get("bbox_json"),
                            structured_data=item_data.get("structured_data"),
                            contact_info_json=item_data.get("contact_info_json"),
                            price_info_json=item_data.get("price_info_json"),
                            date_info_json=item_data.get("date_info_json"),
                            location_info_json=item_data.get("location_info_json"),
                            classification_details_json=item_data.get("classification_details_json"),
                        )
                        db.add(item)
                        total_items += 1

                    if used_ocr:
                        pages_with_ocr += 1

                    page.status = "DONE"
                    page.error_message = None
                except Exception as e:
                    logger.error(f"Page processing failed for page {page_number}: {e}")
                    page.status = "FAILED"
                    page.error_message = str(e)[:500]
                    any_failed = True

                processed_pages += 1
                edition.processed_pages = processed_pages  # type: ignore

                stats["processed_pages"] = processed_pages
                stats["pages_with_ocr"] = pages_with_ocr
                stats["total_items"] = total_items
                extraction_run.stats_json = dict(stats)

                db.commit()
                append_log(f"Page {page_number}/{total_pages} processed")

            doc.close()

            if any_failed and processed_pages == 0:
                raise RuntimeError("All pages failed")

            edition.status = EditionStatus.READY  # type: ignore
            edition.current_stage = "DONE"  # type: ignore
            edition.processed_at = datetime.now(UTC)  # type: ignore

            extraction_run.success = True
            extraction_run.status = "SUCCESS"
            extraction_run.finished_at = datetime.now(UTC)
            extraction_run.completed_at = datetime.now(UTC)
            started_at = extraction_run.started_at or datetime.now(UTC)
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=UTC)

            stats.update({
                "processed_pages": processed_pages,
                "pages_with_ocr": pages_with_ocr,
                "total_items": total_items,
                "processing_time": (datetime.now(UTC) - started_at).total_seconds(),
            })
            extraction_run.stats_json = dict(stats)

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

                    logger.info(
                        f"Classified {classified_count} items with {total_classifications} total classifications"
                    )
            except Exception as e:
                logger.warning(f"Category classification failed: {e}")

            append_log("Processing completed")
            db.commit()
            return True

        except Exception as e:
            logger.error(f"Processing failed for edition {edition_id}: {e}")
            edition.status = EditionStatus.FAILED  # type: ignore
            edition.current_stage = "DONE"  # type: ignore
            edition.last_error = str(e)  # type: ignore
            extraction_run.status = "FAILED"
            extraction_run.error_message = str(e)[:500]
            extraction_run.finished_at = datetime.now(UTC)
            extraction_run.completed_at = datetime.now(UTC)
            db.commit()
            append_log(f"Processing failed: {e}")
            return False


def create_processing_service() -> ProcessingService:
    return ProcessingService()
