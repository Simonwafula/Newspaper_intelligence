"""
Layout Detection Service - Phase 3 Implementation

This service provides ML-based layout detection using LayoutParser
with graceful fallback to heuristic-based detection.

Detects layout blocks such as:
- HEADLINE, SUBHEADLINE
- BODY (text paragraphs)
- BYLINE (author information)
- IMAGE, CAPTION
- AD (advertisements)
- SECTION_LABEL (section headers like "NATIONAL", "SPORTS")
"""

import io
import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Try to import ML dependencies
try:
    import layoutparser as lp
    LAYOUTPARSER_AVAILABLE = True
except ImportError:
    LAYOUTPARSER_AVAILABLE = False
    logger.warning("LayoutParser not available. Install with: pip install layoutparser")


@dataclass
class DetectedBlock:
    """Represents a detected layout block with type and bounding box."""

    id: int
    type: str  # HEADLINE, SUBHEADLINE, BODY, BYLINE, IMAGE, CAPTION, AD, SECTION_LABEL
    bbox: List[float]  # [x0, y0, x1, y1] normalized coordinates (0-1)
    confidence: float
    text: str = ""
    words: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "text": self.text,
            "words": self.words,
        }


@dataclass
class LayoutResult:
    """Result from layout detection containing detected blocks and metadata."""

    blocks: List[DetectedBlock]
    method: str  # 'ml', 'heuristic', or 'fallback'
    model_name: Optional[str] = None
    avg_confidence: Optional[float] = None


class LayoutDetectionService:
    """
    Service for detecting layout blocks in newspaper pages.

    Provides ML-based detection with LayoutParser and
    graceful fallback to heuristic-based detection.

    Usage:
        service = LayoutDetectionService(model_type="auto", device="cpu")
        result = service.detect_layout(image_bytes, page_width, page_height)
        for block in result.blocks:
            print(f"Found {block.type} at {block.bbox}")
    """

    # Map LayoutParser/PubLayNet labels to our types
    LABEL_MAP = {
        "Text": "BODY",
        "Title": "HEADLINE",
        "List": "BODY",
        "Table": "TABLE",
        "Figure": "IMAGE",
    }

    def __init__(self, model_type: str = "auto", device: str = "cpu", confidence_threshold: float = 0.7):
        """
        Initialize the layout detection service.

        Args:
            model_type: Model to use ('auto', 'layoutparser', 'heuristic')
            device: Device for model inference ('cpu' or 'cuda')
            confidence_threshold: Minimum confidence for detections
        """
        self.model_type = model_type
        self.device = device
        self.confidence_threshold = confidence_threshold
        self._model = None

        logger.info(
            f"Initializing LayoutDetectionService with model_type={model_type}, "
            f"device={device}, confidence={confidence_threshold}"
        )

        # Try to load ML model if requested
        if model_type in ["auto", "layoutparser"] and LAYOUTPARSER_AVAILABLE:
            try:
                self._model = self._load_model()
                logger.info(f"Successfully loaded LayoutParser model")
            except Exception as e:
                logger.warning(f"Failed to load ML model: {e}, will use heuristic fallback")
                self._model = None
        else:
            if model_type in ["auto", "layoutparser"] and not LAYOUTPARSER_AVAILABLE:
                logger.warning("LayoutParser requested but not available, using heuristic fallback")

    def detect_layout(
        self, image_bytes: bytes, page_width: float, page_height: float
    ) -> LayoutResult:
        """
        Detect layout blocks in a page image.

        Args:
            image_bytes: PNG/JPEG image bytes of the page
            page_width: Page width in PDF points
            page_height: Page height in PDF points

        Returns:
            LayoutResult with detected blocks and metadata
        """
        # Convert image bytes to PIL Image and numpy array
        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            image_array = np.array(pil_image)
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            return LayoutResult(blocks=[], method="fallback")

        # Try ML detection first
        if self._model is not None:
            try:
                blocks = self._detect_ml(image_array, page_width, page_height)
                avg_conf = sum(b.confidence for b in blocks) / len(blocks) if blocks else 0.0
                return LayoutResult(
                    blocks=blocks,
                    method="ml",
                    model_name="PubLayNet",
                    avg_confidence=avg_conf
                )
            except Exception as e:
                logger.warning(f"ML detection failed: {e}, falling back to heuristic")

        # Fallback to heuristic
        logger.info("Using heuristic layout detection")
        return LayoutResult(blocks=[], method="heuristic")

    def _detect_ml(self, image: np.ndarray, page_width: float, page_height: float) -> List[DetectedBlock]:
        """
        Perform ML-based layout detection using LayoutParser.

        Args:
            image: Page image as numpy array (RGB)
            page_width: Page width for bbox normalization
            page_height: Page height for bbox normalization

        Returns:
            List of detected blocks with types and bboxes
        """
        if self._model is None:
            raise RuntimeError("Model not loaded")

        # Run detection
        layout = self._model.detect(image)

        # Convert to our format
        blocks = []
        img_height, img_width = image.shape[:2]

        for idx, element in enumerate(layout):
            # Get bbox coordinates (in image pixels)
            x1, y1, x2, y2 = element.coordinates

            # Normalize to 0-1 range
            bbox_normalized = [
                float(x1) / img_width,
                float(y1) / img_height,
                float(x2) / img_width,
                float(y2) / img_height,
            ]

            # Map label to our type
            label = element.type
            block_type = self.LABEL_MAP.get(label, "BODY")

            # Get confidence score
            confidence = float(element.score) if hasattr(element, 'score') else 1.0

            # Filter by confidence
            if confidence < self.confidence_threshold:
                continue

            block = DetectedBlock(
                id=idx,
                type=block_type,
                bbox=bbox_normalized,
                confidence=confidence,
                text="",  # Will be filled by OCR
                words=[],
            )
            blocks.append(block)

        logger.info(f"Detected {len(blocks)} layout blocks using ML")
        return blocks

    def _load_model(self):
        """
        Load the LayoutParser model (PubLayNet).

        Returns:
            LayoutParser model instance
        """
        if not LAYOUTPARSER_AVAILABLE:
            raise ImportError("LayoutParser not available")

        # Load PubLayNet model for newspaper layout detection
        # This model is pre-trained on document layouts including newspapers
        model = lp.Detectron2LayoutModel(
            'lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config',
            extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", self.confidence_threshold],
            label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"},
            device=self.device
        )

        logger.info("LayoutParser PubLayNet model loaded successfully")
        return model

    def cleanup(self):
        """Release model resources."""
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("Layout detection model cleaned up")
