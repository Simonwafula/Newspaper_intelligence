import logging
import os
from datetime import UTC, datetime

import fitz
from sqlalchemy.orm import Session

from app.models import Edition, ExtractionRun, Item, Page
from app.schemas import EditionStatus
from app.services.block_ocr_service import BlockOCRService
from app.services.category_classifier import CategoryClassifier
from app.services.layout_analyzer import create_layout_analyzer
from app.services.layout_detection_service import LayoutDetectionService
from app.services.ocr_service import create_ocr_service
from app.services.pdf_processor import create_pdf_processor
from app.services.reading_order_service import ReadingOrderService
from app.services.story_grouping import persist_story_groups
from app.settings import settings

logger = logging.getLogger(__name__)


class ProcessingService:
    """Main service for processing PDF editions."""

    def __init__(self):
        self.pdf_processor = create_pdf_processor(settings.min_chars_for_native_text)
        self.ocr_service = create_ocr_service(settings.ocr_languages) if settings.ocr_enabled else None
        self.layout_analyzer = create_layout_analyzer()

        # Phase 2: Initialize reading order service
        self.reading_order = (
            ReadingOrderService() if settings.advanced_layout_enabled else None
        )

        # Phase 3: Initialize layout detection service
        self.layout_detector = None
        if settings.advanced_layout_enabled and settings.layout_detection_method != "heuristic":
            try:
                self.layout_detector = LayoutDetectionService(
                    model_type=settings.layout_detection_method,
                    device=settings.layout_model_device,
                    confidence_threshold=settings.layout_confidence_threshold,
                )
                logger.info("Layout detection service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize layout detection: {e}, will use heuristic")
                self.layout_detector = None

        # Phase 4: Initialize block OCR service
        self.block_ocr = None
        if settings.advanced_layout_enabled and settings.block_ocr_enabled:
            try:
                self.block_ocr = BlockOCRService(
                    prefer_paddle=(settings.block_ocr_engine == "paddle"),
                    lang=settings.block_ocr_lang if hasattr(settings, 'block_ocr_lang') else 'en',
                    use_gpu=(settings.layout_model_device == "cuda"),
                    confidence_threshold=getattr(settings, 'block_ocr_confidence_threshold', 0.5),
                )
                logger.info("Block OCR service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize block OCR: {e}, will use fallback")
                self.block_ocr = None

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
            edition.num_pages = total_pages  # type: ignore
            edition.pages_processed = 0  # type: ignore
            edition.processed_pages = 0  # type: ignore
            db.commit()

            stats = {
                "total_pages": total_pages,
                "processed_pages": 0,
                "pages_with_ocr": 0,
                "total_items": 0,
                "ocr_avg_confidence": None,
                "ocr_low_conf_pages": 0,
                "pages_with_fallback_ocr": 0,
            }
            extraction_run.stats_json = dict(stats)
            db.commit()

            total_items = 0
            pages_with_ocr = 0
            processed_pages = 0
            any_failed = False
            ocr_conf_sum = 0.0
            ocr_conf_pages = 0
            ocr_low_conf_pages = 0
            pages_with_fallback_ocr = 0

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
                    # ========== STAGE 1: HIGH-DPI RENDERING (Phase 2) ==========
                    high_res_image_path = None
                    if settings.advanced_layout_enabled:
                        edition.current_stage = "RENDER"  # type: ignore
                        db.commit()

                        # Render at high DPI or target width for layout detection
                        render_dpi = settings.layout_detection_dpi
                        target_width = settings.layout_detection_width if settings.layout_detection_width > 0 else None

                        high_res_bytes = self.pdf_processor.get_page_image(
                            pdf_path,
                            page_index,
                            dpi=render_dpi,
                            target_width=target_width,
                        )

                        # Store high-res image
                        pages_dir = os.path.join(settings.storage_path, "pages")
                        os.makedirs(pages_dir, exist_ok=True)
                        high_res_image_path = os.path.join(
                            pages_dir, f"{edition_id}_{page_number}_hires.png"
                        )
                        with open(high_res_image_path, "wb") as f:
                            f.write(high_res_bytes)

                        # Store metadata
                        page.high_res_image_path = high_res_image_path
                        page.render_dpi = render_dpi if target_width is None else None
                        page.render_width_px = target_width
                        page.layout_method = "heuristic"  # Will be updated to "ml" in Phase 3

                        logger.info(
                            f"Page {page_number}: Rendered at "
                            f"{f'{render_dpi} DPI' if target_width is None else f'{target_width}px width'}"
                        )

                    # ========== STAGE 1.5: LAYOUT DETECTION (Phase 3) ==========
                    detected_blocks = None
                    if settings.advanced_layout_enabled and self.layout_detector and high_res_image_path:
                        edition.current_stage = "LAYOUT_DETECT"  # type: ignore
                        db.commit()

                        try:
                            # Run ML-based layout detection on high-res image
                            with open(high_res_image_path, "rb") as f:
                                high_res_bytes_for_detection = f.read()

                            layout_result = self.layout_detector.detect_layout(
                                high_res_bytes_for_detection,
                                page_data.get("width", 0),
                                page_data.get("height", 0),
                            )

                            detected_blocks = layout_result.blocks
                            page.layout_model_used = layout_result.model_name
                            page.layout_method = layout_result.method
                            page.layout_confidence = layout_result.avg_confidence

                            logger.info(
                                f"Page {page_number}: Detected {len(detected_blocks)} blocks "
                                f"using {layout_result.method} (confidence: {layout_result.avg_confidence:.2f})"
                            )
                        except Exception as e:
                            logger.warning(f"Layout detection failed for page {page_number}: {e}")
                            detected_blocks = None
                            page.layout_method = "heuristic"

                    # ========== STAGE 4: BLOCK-LEVEL OCR (Phase 4) ==========
                    if (
                        settings.advanced_layout_enabled
                        and settings.block_ocr_enabled
                        and self.block_ocr
                        and detected_blocks
                        and high_res_image_path
                    ):
                        edition.current_stage = "BLOCK_OCR"  # type: ignore
                        db.commit()

                        try:
                            # Load high-res image as numpy array
                            import numpy as np
                            from PIL import Image as PILImage

                            with PILImage.open(high_res_image_path) as img:
                                if img.mode != 'RGB':
                                    img = img.convert('RGB')
                                high_res_array = np.array(img)

                            # Run block-level OCR on detected blocks
                            ocr_results = self.block_ocr.batch_extract(detected_blocks, high_res_array)

                            # Update blocks with OCR text and words
                            for block, ocr_result in zip(detected_blocks, ocr_results):
                                block.text = ocr_result.text
                                block.words = ocr_result.words

                            # Store OCR words in page.ocr_words_json
                            # Format: [{"text": "...", "bbox": [...], "confidence": 0.95, "block_id": 123}, ...]
                            all_words = []
                            for block in detected_blocks:
                                for word in block.words:
                                    all_words.append({
                                        "text": word["text"],
                                        "bbox": word["bbox"],
                                        "confidence": word["confidence"],
                                        "block_id": block.id,
                                    })

                            page.ocr_words_json = all_words

                            # Calculate stats
                            total_confidence = sum(w["confidence"] for w in all_words)
                            avg_conf = total_confidence / len(all_words) if all_words else 0.0

                            logger.info(
                                f"Page {page_number}: Block OCR extracted {len(all_words)} words "
                                f"from {len(detected_blocks)} blocks (avg conf: {avg_conf:.2f})"
                            )

                        except Exception as e:
                            logger.warning(f"Block OCR failed for page {page_number}: {e}")
                            page.ocr_words_json = None

                    # ========== STAGE 2: EXTRACT (EXISTING) ==========
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
                        def _score(result: dict) -> tuple[float, int]:
                            conf = result.get("avg_confidence")
                            conf_score = conf if conf is not None else -1.0
                            return (conf_score, result.get("word_count", 0))

                        ocr_result = self.ocr_service.extract_text_with_boxes(
                            image_bytes,
                            preprocess=settings.ocr_preprocess,
                            psm=settings.ocr_psm,
                        )

                        if settings.ocr_retry_enabled:
                            avg_conf = ocr_result.get("avg_confidence")
                            if avg_conf is None or avg_conf < settings.ocr_confidence_threshold:
                                retry_bytes = self.pdf_processor.get_page_image(
                                    pdf_path, page_index, dpi=settings.ocr_retry_dpi
                                )
                                retry_result = self.ocr_service.extract_text_with_boxes(
                                    retry_bytes,
                                    preprocess=settings.ocr_preprocess,
                                    psm=settings.ocr_retry_psm,
                                )

                                if _score(retry_result) > _score(ocr_result):
                                    image_bytes = retry_bytes
                                    ocr_result = retry_result

                        if settings.ocr_fallback_enabled:
                            avg_conf = ocr_result.get("avg_confidence")
                            if avg_conf is None or avg_conf < settings.ocr_confidence_threshold:
                                try:
                                    fallback_result = self.ocr_service.extract_text_with_boxes_fallback(
                                        image_bytes,
                                        preprocess=settings.ocr_preprocess,
                                    )
                                    if _score(fallback_result) > _score(ocr_result):
                                        ocr_result = fallback_result
                                        pages_with_fallback_ocr += 1
                                except Exception as e:
                                    logger.warning(f"Fallback OCR failed for page {page_number}: {e}")

                        pages_dir = os.path.join(settings.storage_path, "pages")
                        os.makedirs(pages_dir, exist_ok=True)
                        image_path = os.path.join(pages_dir, f"{edition_id}_{page_number}.png")
                        with open(image_path, "wb") as f:
                            f.write(image_bytes)

                        page_data["extracted_text"] = ocr_result["text"]
                        page_data["text_blocks"].extend(ocr_result["text_blocks"])
                        page_data["ocr_meta"] = {
                            "avg_confidence": ocr_result.get("avg_confidence"),
                            "word_count": ocr_result.get("word_count"),
                            "psm": ocr_result.get("psm"),
                            "preprocess": ocr_result.get("preprocess"),
                            "engine": ocr_result.get("engine"),
                        }
                        used_ocr = True

                    edition.current_stage = "LAYOUT"  # type: ignore
                    db.commit()

                    try:
                        page_data = self.layout_analyzer.analyze_page(page_data)
                    except Exception as e:
                        logger.error(f"Layout analysis failed for page {page_number}: {e}")
                        page_data["extracted_items"] = []

                    # ========== STAGE 3: READING ORDER (Phase 2) ==========
                    if settings.reading_order_enabled and self.reading_order:
                        try:
                            text_blocks = page_data.get("text_blocks", [])
                            if text_blocks:
                                # Assign reading order to text blocks
                                ordered_blocks = self.reading_order.assign_reading_order(
                                    text_blocks, page_data.get("width", 0)
                                )
                                page_data["text_blocks"] = ordered_blocks
                                logger.debug(
                                    f"Page {page_number}: Assigned reading order to {len(ordered_blocks)} blocks"
                                )
                        except Exception as e:
                            logger.warning(f"Reading order assignment failed for page {page_number}: {e}")

                    edition.current_stage = "INDEX"  # type: ignore
                    db.commit()

                    page.extracted_text = page_data.get("extracted_text")
                    page.bbox_json = {
                        "text_blocks": page_data.get("text_blocks", []),
                        "ocr_meta": page_data.get("ocr_meta"),
                    }
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
                        avg_conf = (page_data.get("ocr_meta") or {}).get("avg_confidence")
                        if isinstance(avg_conf, (int, float)):
                            ocr_conf_sum += float(avg_conf)
                            ocr_conf_pages += 1
                            if avg_conf < settings.ocr_confidence_threshold:
                                ocr_low_conf_pages += 1

                    page.status = "DONE"
                    page.error_message = None
                except Exception as e:
                    logger.error(f"Page processing failed for page {page_number}: {e}")
                    page.status = "FAILED"
                    page.error_message = str(e)[:500]
                    any_failed = True

                processed_pages += 1
                edition.processed_pages = processed_pages  # type: ignore
                edition.pages_processed = processed_pages  # type: ignore

                stats["processed_pages"] = processed_pages
                stats["pages_with_ocr"] = pages_with_ocr
                stats["total_items"] = total_items
                stats["ocr_low_conf_pages"] = ocr_low_conf_pages
                stats["pages_with_fallback_ocr"] = pages_with_fallback_ocr
                if ocr_conf_pages:
                    stats["ocr_avg_confidence"] = round(ocr_conf_sum / ocr_conf_pages, 2)
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

            if settings.story_grouping_enabled:
                try:
                    grouped_count = persist_story_groups(db, edition_id)
                    logger.info("Persisted %s story groups", grouped_count)
                except Exception as e:
                    logger.warning(f"Story grouping failed: {e}")

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


def reprocess_single_page(edition_id: int, page_number: int, db: Session) -> bool:
    """
    Reprocess a single page for an edition (OCR + layout + items).
    """
    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        logger.error("Edition %s not found for page reprocess", edition_id)
        return False

    pdf_path = edition.pdf_local_path or edition.file_path
    if not pdf_path or not os.path.exists(pdf_path):
        logger.error("Local PDF missing for edition %s", edition_id)
        return False

    if page_number < 1:
        logger.error("Invalid page number %s", page_number)
        return False

    processing_service = ProcessingService()

    try:
        doc = fitz.open(pdf_path)
        if page_number > len(doc):
            logger.error("Page number %s out of range", page_number)
            doc.close()
            return False

        page_index = page_number - 1

        page = (
            db.query(Page)
            .filter(Page.edition_id == edition_id, Page.page_number == page_number)
            .first()
        )
        if not page:
            page = Page(edition_id=edition_id, page_number=page_number)
            db.add(page)
            db.flush()

        page.status = "PROCESSING"
        db.commit()

        page_data = processing_service.pdf_processor.get_page_data(doc, page_index)
        used_ocr = False
        image_path = None

        if page_data.get("needs_ocr") and processing_service.ocr_service and processing_service.ocr_service.is_available():
            image_bytes = processing_service.pdf_processor.get_page_image(
                pdf_path, page_index, dpi=settings.ocr_image_dpi
            )

            def _score(result: dict) -> tuple[float, int]:
                conf = result.get("avg_confidence")
                conf_score = conf if conf is not None else -1.0
                return (conf_score, result.get("word_count", 0))

            ocr_result = processing_service.ocr_service.extract_text_with_boxes(
                image_bytes,
                preprocess=settings.ocr_preprocess,
                psm=settings.ocr_psm,
            )

            if settings.ocr_retry_enabled:
                avg_conf = ocr_result.get("avg_confidence")
                if avg_conf is None or avg_conf < settings.ocr_confidence_threshold:
                    retry_bytes = processing_service.pdf_processor.get_page_image(
                        pdf_path, page_index, dpi=settings.ocr_retry_dpi
                    )
                    retry_result = processing_service.ocr_service.extract_text_with_boxes(
                        retry_bytes,
                        preprocess=settings.ocr_preprocess,
                        psm=settings.ocr_retry_psm,
                    )
                    if _score(retry_result) > _score(ocr_result):
                        image_bytes = retry_bytes
                        ocr_result = retry_result

            if settings.ocr_fallback_enabled:
                avg_conf = ocr_result.get("avg_confidence")
                if avg_conf is None or avg_conf < settings.ocr_confidence_threshold:
                    try:
                        fallback_result = processing_service.ocr_service.extract_text_with_boxes_fallback(
                            image_bytes,
                            preprocess=settings.ocr_preprocess,
                        )
                        if _score(fallback_result) > _score(ocr_result):
                            ocr_result = fallback_result
                    except Exception as e:
                        logger.warning("Fallback OCR failed for page %s: %s", page_number, e)

            pages_dir = os.path.join(settings.storage_path, "pages")
            os.makedirs(pages_dir, exist_ok=True)
            image_path = os.path.join(pages_dir, f"{edition_id}_{page_number}.png")
            with open(image_path, "wb") as f:
                f.write(image_bytes)

            page_data["extracted_text"] = ocr_result["text"]
            page_data["text_blocks"].extend(ocr_result["text_blocks"])
            page_data["ocr_meta"] = {
                "avg_confidence": ocr_result.get("avg_confidence"),
                "word_count": ocr_result.get("word_count"),
                "psm": ocr_result.get("psm"),
                "preprocess": ocr_result.get("preprocess"),
                "engine": ocr_result.get("engine"),
            }
            used_ocr = True

        try:
            page_data = processing_service.layout_analyzer.analyze_page(page_data)
        except Exception as e:
            logger.error("Layout analysis failed for page %s: %s", page_number, e)
            page_data["extracted_items"] = []

        db.query(Item).filter(Item.edition_id == edition_id, Item.page_number == page_number).delete()
        db.commit()

        page.extracted_text = page_data.get("extracted_text")
        page.bbox_json = {
            "text_blocks": page_data.get("text_blocks", []),
            "ocr_meta": page_data.get("ocr_meta"),
        }
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

        page.status = "DONE"
        page.error_message = None
        db.commit()
        doc.close()
        return True
    except Exception as e:
        logger.error("Page reprocess failed for edition %s page %s: %s", edition_id, page_number, e)
        page = (
            db.query(Page)
            .filter(Page.edition_id == edition_id, Page.page_number == page_number)
            .first()
        )
        if page:
            page.status = "FAILED"
            page.error_message = str(e)[:500]
            db.commit()
        return False
