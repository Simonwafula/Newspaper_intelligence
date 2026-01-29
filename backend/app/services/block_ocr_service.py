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

import logging
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


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

    def __init__(self, prefer_paddle: bool = True):
        """
        Initialize the block OCR service.

        Args:
            prefer_paddle: If True, use PaddleOCR; if False or unavailable, use Tesseract
        """
        self.prefer_paddle = prefer_paddle
        self._paddle = None
        self._tesseract = None

        logger.info(f"Initializing BlockOCRService with prefer_paddle={prefer_paddle}")

        # TODO Phase 4: Initialize OCR engines
        # if prefer_paddle:
        #     try:
        #         from paddleocr import PaddleOCR
        #         self._paddle = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        #     except Exception as e:
        #         logger.warning(f"PaddleOCR not available: {e}, will use Tesseract")
        #
        # if not self._paddle:
        #     from app.services.ocr_service import OCRService
        #     self._tesseract = OCRService()

    def extract_block_text(
        self, block: "DetectedBlock", full_image: np.ndarray
    ) -> BlockOCRResult:
        """
        Extract text from a single block with word-level coordinates.

        Args:
            block: DetectedBlock with bbox to extract
            full_image: Full page image as numpy array

        Returns:
            BlockOCRResult with text, words, and confidence

        Implementation Notes (Phase 4):
            1. Crop block from full image using block.bbox
            2. If PaddleOCR available:
               - Run paddle.ocr(block_image, cls=True)
               - Extract words with bboxes and confidence
               - Convert bbox coordinates to page-relative
            3. Else use Tesseract:
               - Convert to PIL Image
               - Call tesseract with word-level output
               - Parse result to get words + bboxes
            4. Calculate average confidence
            5. Return BlockOCRResult
        """
        raise NotImplementedError(
            "Phase 4: Implement block-level OCR with PaddleOCR. "
            "See plan file for detailed implementation guidance."
        )

    def batch_extract(
        self, blocks: List["DetectedBlock"], image: np.ndarray
    ) -> List[BlockOCRResult]:
        """
        Extract text from multiple blocks in parallel.

        Args:
            blocks: List of DetectedBlock objects
            image: Full page image

        Returns:
            List of BlockOCRResult in same order as input blocks

        Implementation Notes (Phase 4):
            1. For small number of blocks (<5), process sequentially
            2. For larger batches:
               - Use ThreadPoolExecutor for I/O-bound OCR operations
               - Or process in batches if memory-constrained
            3. Maintain order in results
            4. Handle individual block failures gracefully
        """
        raise NotImplementedError("Phase 4: Implement batch OCR processing")

    def _extract_with_paddle(self, block_image: np.ndarray) -> BlockOCRResult:
        """
        Extract text using PaddleOCR.

        Args:
            block_image: Cropped block image

        Returns:
            BlockOCRResult

        Implementation Notes (Phase 4):
            PaddleOCR returns structure like:
            [
                [[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], ("word", confidence)],
                ...
            ]

            Need to:
            1. Convert polygon to bbox [x0, y0, x1, y1]
            2. Extract text and confidence
            3. Build words list
            4. Concatenate all text
        """
        raise NotImplementedError("Phase 4: Implement PaddleOCR extraction")

    def _extract_with_tesseract(self, block_image: Image.Image) -> BlockOCRResult:
        """
        Extract text using Tesseract (fallback).

        Args:
            block_image: Cropped block as PIL Image

        Returns:
            BlockOCRResult

        Implementation Notes (Phase 4):
            Use pytesseract.image_to_data() with output_type=Output.DICT
            to get word-level bboxes:
            {
                'text': [...],
                'left': [...],
                'top': [...],
                'width': [...],
                'height': [...],
                'conf': [...]
            }

            Build words list from this data.
        """
        raise NotImplementedError("Phase 4: Implement Tesseract extraction")

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
        if self._tesseract is not None:
            self._tesseract = None
        logger.info("Block OCR service cleaned up")
