"""
Block OCR Service - Phase 4 Implementation

This service performs OCR on individual layout blocks with word-level coordinates.
Uses PaddleOCR (preferred) with graceful fallback to existing Tesseract service.

Advantages of block-level OCR:
- Better reading order preservation
- Higher accuracy on structured layouts
- Word-level bounding boxes for highlighting
- Per-block confidence scoring
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    import numpy as np
    from PIL import Image

logger = logging.getLogger(__name__)

# Try to import PaddleOCR
PADDLEOCR_AVAILABLE = False
PaddleOCR = None
np = None
PILImage = None

try:
    from paddleocr import PaddleOCR as _PaddleOCR
    import numpy as np
    from PIL import Image as PILImage
    PaddleOCR = _PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"PaddleOCR not available: {e}. Will use Tesseract fallback.")


@dataclass
class BlockOCRResult:
    """Result from OCR on a single block."""

    text: str
    words: List[dict]  # [{"text": "...", "bbox": [x0,y0,x1,y1], "confidence": 0.95}, ...]
    confidence: float  # Average confidence across all words
    engine: str  # 'paddle', 'tesseract', or 'fallback'


class BlockOCRService:
    """
    Service for performing OCR on detected layout blocks.

    Provides word-level coordinates and confidence scores.
    Uses PaddleOCR as primary engine with Tesseract fallback.

    Usage:
        service = BlockOCRService(prefer_paddle=True)
        result = service.extract_block_text(block, full_page_image)
        print(f"Extracted: {result.text} with confidence {result.confidence}")
    """

    def __init__(
        self,
        prefer_paddle: bool = True,
        lang: str = 'en',
        use_gpu: bool = False,
        confidence_threshold: float = 0.5
    ):
        """
        Initialize the block OCR service.

        Args:
            prefer_paddle: If True, use PaddleOCR; if False or unavailable, use Tesseract
            lang: Language code for OCR (default 'en')
            use_gpu: Use GPU for PaddleOCR (default False)
            confidence_threshold: Minimum confidence to keep words (default 0.5)
        """
        self.prefer_paddle = prefer_paddle
        self.lang = lang
        self.use_gpu = use_gpu
        self.confidence_threshold = confidence_threshold
        self._paddle = None
        self._tesseract = None

        logger.info(
            f"Initializing BlockOCRService with prefer_paddle={prefer_paddle}, "
            f"lang={lang}, use_gpu={use_gpu}"
        )

        # Initialize OCR engines
        if prefer_paddle and PADDLEOCR_AVAILABLE and PaddleOCR is not None:
            try:
                self._paddle = PaddleOCR(
                    use_angle_cls=True,
                    lang=lang,
                    use_gpu=use_gpu,
                    show_log=False
                )
                logger.info("PaddleOCR initialized successfully")
            except Exception as e:
                logger.warning(f"PaddleOCR not available: {e}, will use Tesseract")

        if not self._paddle:
            try:
                from app.services.ocr_service import OCRService
                self._tesseract = OCRService()
                logger.info("Using Tesseract fallback")
            except Exception as e:
                logger.warning(f"Tesseract also unavailable: {e}")

    def extract_block_text(
        self, block: "DetectedBlock", full_image: "np.ndarray"
    ) -> BlockOCRResult:
        """
        Extract text from a single block with word-level coordinates.

        Args:
            block: DetectedBlock with bbox to extract
            full_image: Full page image as numpy array

        Returns:
            BlockOCRResult with text, words, and confidence
        """
        if not PADDLEOCR_AVAILABLE or np is None or PILImage is None:
            return self._extract_fallback()

        # Get image dimensions
        img_height, img_width = full_image.shape[:2]

        # Crop block from full image
        block_image = self._crop_block(full_image, block.bbox, img_width, img_height)

        # Try PaddleOCR first
        if self._paddle is not None:
            try:
                return self._extract_with_paddle_impl(block_image, block.bbox, img_width, img_height)
            except Exception as e:
                logger.warning(f"PaddleOCR extraction failed: {e}, using fallback")

        # Fallback
        return self._extract_fallback()

    def batch_extract(
        self, blocks: List["DetectedBlock"], image: "np.ndarray"
    ) -> List[BlockOCRResult]:
        """
        Extract text from multiple blocks in parallel.

        Args:
            blocks: List of DetectedBlock objects
            image: Full page image

        Returns:
            List of BlockOCRResult in same order as input blocks
        """
        results = []
        for block in blocks:
            try:
                result = self.extract_block_text(block, image)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to extract text from block {block.id}: {e}")
                results.append(self._extract_fallback())
        return results

    def _extract_with_paddle_impl(
        self,
        block_image: "np.ndarray",
        block_bbox: List[float],
        page_width: int,
        page_height: int
    ) -> BlockOCRResult:
        """
        Extract text using PaddleOCR with word-level coordinates.

        Args:
            block_image: Cropped block image as numpy array
            block_bbox: Original normalized bbox of the block in page coordinates
            page_width: Full page width for coordinate conversion
            page_height: Full page height for coordinate conversion

        Returns:
            BlockOCRResult with words and confidence
        """
        if self._paddle is None:
            raise RuntimeError("PaddleOCR not initialized")

        # Run PaddleOCR on the block
        paddle_result = self._paddle.ocr(block_image, cls=True)

        if not paddle_result or not paddle_result[0]:
            logger.debug("PaddleOCR returned no results for block")
            return BlockOCRResult(text="", words=[], confidence=0.0, engine="paddle")

        # Parse results
        words = []
        full_text_lines = []
        confidences = []

        block_height, block_width = block_image.shape[:2]

        for line_data in paddle_result[0]:
            if not line_data:
                continue

            bbox_coords = line_data[0]  # [[x0,y0], [x1,y1], [x2,y2], [x3,y3]]
            text_info = line_data[1]    # (text, confidence)

            text = text_info[0].strip()
            if not text:
                continue

            confidence = float(text_info[1])

            # Skip low confidence detections
            if confidence < self.confidence_threshold:
                continue

            # Convert PaddleOCR bbox (4 corner points in block coords) to normalized page coords
            # 1. Get bounding box in block image coordinates
            x_coords = [pt[0] for pt in bbox_coords]
            y_coords = [pt[1] for pt in bbox_coords]
            block_x0 = min(x_coords)
            block_y0 = min(y_coords)
            block_x1 = max(x_coords)
            block_y1 = max(y_coords)

            # 2. Convert from block coordinates to page coordinates
            # block_bbox is [x0, y0, x1, y1] in normalized page coords
            block_x0_norm = block_bbox[0]
            block_y0_norm = block_bbox[1]
            block_x1_norm = block_bbox[2]
            block_y1_norm = block_bbox[3]

            # Width and height of block in normalized coordinates
            block_width_norm = block_x1_norm - block_x0_norm
            block_height_norm = block_y1_norm - block_y0_norm

            # Convert word bbox from block coords to page coords
            word_x0 = block_x0_norm + (block_x0 / block_width) * block_width_norm
            word_y0 = block_y0_norm + (block_y0 / block_height) * block_height_norm
            word_x1 = block_x0_norm + (block_x1 / block_width) * block_width_norm
            word_y1 = block_y0_norm + (block_y1 / block_height) * block_height_norm

            bbox_normalized = [word_x0, word_y0, word_x1, word_y1]

            word_dict = {
                "text": text,
                "bbox": bbox_normalized,
                "confidence": confidence
            }

            words.append(word_dict)
            full_text_lines.append(text)
            confidences.append(confidence)

        # Calculate average confidence
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        # Join text with newlines (PaddleOCR detects lines)
        full_text = "\n".join(full_text_lines)

        logger.debug(
            f"PaddleOCR detected {len(words)} text lines, "
            f"avg confidence: {avg_conf:.2f}"
        )

        return BlockOCRResult(
            text=full_text,
            words=words,
            confidence=avg_conf,
            engine="paddle"
        )

    def _extract_fallback(self) -> BlockOCRResult:
        """
        Return empty result when OCR not available.

        Returns:
            Empty BlockOCRResult indicating fallback to existing Tesseract service
        """
        return BlockOCRResult(
            text="",
            words=[],
            confidence=0.0,
            engine="fallback"
        )


    def _crop_block(
        self, full_image: np.ndarray, bbox: List[float], page_width: float, page_height: float
    ) -> np.ndarray:
        """
        Crop a block from the full page image.

        Args:
            full_image: Full page image
            bbox: Normalized bbox [x0, y0, x1, y1] in 0-1 range
            page_width: Page width in pixels
            page_height: Page height in pixels

        Returns:
            Cropped block image

        Implementation:
            x0_px = int(bbox[0] * page_width)
            y0_px = int(bbox[1] * page_height)
            x1_px = int(bbox[2] * page_width)
            y1_px = int(bbox[3] * page_height)
            return full_image[y0_px:y1_px, x0_px:x1_px]
        """
        x0_px = int(bbox[0] * page_width)
        y0_px = int(bbox[1] * page_height)
        x1_px = int(bbox[2] * page_width)
        y1_px = int(bbox[3] * page_height)

        # Ensure bounds are within image
        x0_px = max(0, min(x0_px, page_width - 1))
        x1_px = max(0, min(x1_px, page_width))
        y0_px = max(0, min(y0_px, page_height - 1))
        y1_px = max(0, min(y1_px, page_height))

        return full_image[y0_px:y1_px, x0_px:x1_px]

    def cleanup(self):
        """Release OCR engine resources."""
        if self._paddle is not None:
            del self._paddle
            self._paddle = None
            logger.info("PaddleOCR model cleaned up")
        if self._tesseract is not None:
            self._tesseract = None
        logger.info("Block OCR service cleaned up")
