import logging

from app.settings import settings

try:
    import io
    import pytesseract
    from PIL import Image, ImageFilter, ImageOps
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("Tesseract OCR not available. Install with: pip install pytesseract pillow")

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PaddleOCR = None
    PADDLE_AVAILABLE = False

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    OPENCV_AVAILABLE = False

logger = logging.getLogger(__name__)


class OCRService:
    """Handles OCR processing for scanned PDF pages."""

    def __init__(self, languages: str = "eng"):
        """
        Initialize OCR service.

        Args:
            languages: Tesseract language codes (e.g., "eng", "eng+fra")
        """
        self.languages = languages
        self.available = TESSERACT_AVAILABLE

        if not self.available:
            logger.warning("OCR functionality disabled - Tesseract not installed")
        else:
            if settings.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
            # Test if tesseract is actually available
            try:
                pytesseract.get_tesseract_version()
                logger.info(f"Tesseract OCR available, languages: {languages}")
            except Exception as e:
                logger.error(f"Tesseract OCR not properly configured: {e}")
                self.available = False

        self._paddle: PaddleOCR | None = None
        if settings.ocr_fallback_enabled and not PADDLE_AVAILABLE:
            logger.warning("PaddleOCR fallback enabled but paddleocr is not installed")

    def extract_text_from_image(self, image_bytes: bytes) -> str:
        """
        Extract text from image bytes using OCR.

        Args:
            image_bytes: PNG image bytes

        Returns:
            Extracted text string
        """
        if not self.available:
            raise RuntimeError("OCR not available - Tesseract not installed or configured")

        try:
            # Open image from bytes
            image = Image.open(io.BytesIO(image_bytes))

            # Extract text using Tesseract
            text = pytesseract.image_to_string(image, lang=self.languages)

            return text.strip()

        except Exception as e:
            logger.error(f"Error extracting text with OCR: {e}")
            raise

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        image = ImageOps.grayscale(image)
        image = ImageOps.autocontrast(image)
        if settings.ocr_preprocess_unsharp:
            image = image.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        else:
            image = image.filter(ImageFilter.SHARPEN)

        if settings.ocr_preprocess_adaptive and OPENCV_AVAILABLE:
            img = np.array(image)
            img = cv2.medianBlur(img, 3)
            img = cv2.adaptiveThreshold(
                img,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                10,
            )
            return Image.fromarray(img)

        threshold = max(0, min(255, settings.ocr_preprocess_global_threshold))
        image = image.point(lambda p: 255 if p > threshold else 0)
        return image

    def extract_text_with_boxes(
        self,
        image_bytes: bytes,
        *,
        preprocess: bool = True,
        psm: int = 3,
        conf_threshold: int = 30,
    ) -> dict:
        """
        Extract text with bounding box information.

        Args:
            image_bytes: PNG image bytes

        Returns:
            Dictionary with extracted text and position information
        """
        if not self.available:
            raise RuntimeError("OCR not available - Tesseract not installed or configured")

        try:
            # Open image from bytes
            image = Image.open(io.BytesIO(image_bytes))
            if preprocess:
                image = self._preprocess_image(image)

            # Get detailed OCR data with bounding boxes
            config = f"--psm {psm}"
            data = pytesseract.image_to_data(
                image,
                lang=self.languages,
                config=config,
                output_type=pytesseract.Output.DICT,
            )

            # Process the data to extract text blocks
            text_blocks = []
            current_text = ""
            current_bbox = None

            conf_values = []
            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                if not text:
                    if current_text:
                        # Save the current text block
                        if current_bbox:
                            text_blocks.append({
                                'text': current_text.strip(),
                                'bbox': current_bbox,
                                'type': 'ocr_text'
                            })
                        current_text = ""
                        current_bbox = None
                    continue

                conf = int(data["conf"][i])
                if conf >= 0:
                    conf_values.append(conf)
                if conf > conf_threshold:  # Only include text with confidence > threshold
                    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]

                    if not current_text:
                        current_text = text
                        current_bbox = [x, y, x + w, y + h]
                    else:
                        # Extend bounding box
                        current_bbox[2] = max(current_bbox[2], x + w)
                        current_bbox[3] = max(current_bbox[3], y + h)
                        current_text += " " + text
                else:
                    # Low confidence text - start new block
                    if current_text:
                        text_blocks.append({
                            'text': current_text.strip(),
                            'bbox': current_bbox,
                            'type': 'ocr_text'
                        })
                        current_text = ""
                        current_bbox = None

            # Add the last text block if any
            if current_text and current_bbox:
                text_blocks.append({
                    'text': current_text.strip(),
                    'bbox': current_bbox,
                    'type': 'ocr_text'
                })

            # Combine all text for simple extraction
            full_text = " ".join([block["text"] for block in text_blocks])
            avg_conf = round(sum(conf_values) / len(conf_values), 2) if conf_values else None

            return {
                "text": full_text,
                "text_blocks": text_blocks,
                "avg_confidence": avg_conf,
                "word_count": len(full_text.split()),
                "psm": psm,
                "preprocess": preprocess,
                "engine": "tesseract",
            }

        except Exception as e:
            logger.error(f"Error extracting OCR text with boxes: {e}")
            # Fallback to simple text extraction
            return {
                "text": self.extract_text_from_image(image_bytes),
                "text_blocks": [],
                "avg_confidence": None,
                "word_count": 0,
                "psm": psm,
                "preprocess": preprocess,
                "engine": "tesseract",
            }

    def is_available(self) -> bool:
        """Check if OCR service is available."""
        return self.available

    def _get_paddle(self):
        if not settings.ocr_fallback_enabled or not PADDLE_AVAILABLE:
            return None
        if self._paddle is None:
            try:
                self._paddle = PaddleOCR(use_angle_cls=True, lang=settings.ocr_fallback_lang)
            except Exception as e:
                logger.error(f"Failed to initialize PaddleOCR: {e}")
                return None
        return self._paddle

    def extract_text_with_boxes_fallback(
        self,
        image_bytes: bytes,
        *,
        preprocess: bool = True,
    ) -> dict:
        paddle = self._get_paddle()
        if paddle is None:
            raise RuntimeError("PaddleOCR not available")

        try:
            image = Image.open(io.BytesIO(image_bytes))
            if preprocess:
                image = self._preprocess_image(image)
            image = image.convert("RGB")
            img = np.array(image)

            result = paddle.ocr(img, cls=True)
            text_blocks = []
            conf_values = []
            for line in result or []:
                if not line or len(line) < 2:
                    continue
                box, (text, conf) = line
                if text:
                    xs = [point[0] for point in box]
                    ys = [point[1] for point in box]
                    text_blocks.append({
                        "text": text,
                        "bbox": [min(xs), min(ys), max(xs), max(ys)],
                        "type": "ocr_text",
                    })
                    conf_values.append(conf)

            full_text = " ".join([block["text"] for block in text_blocks])
            avg_conf = round(sum(conf_values) / len(conf_values), 4) if conf_values else None

            return {
                "text": full_text,
                "text_blocks": text_blocks,
                "avg_confidence": avg_conf,
                "word_count": len(full_text.split()),
                "psm": None,
                "preprocess": preprocess,
                "engine": "paddle",
            }
        except Exception as e:
            logger.error(f"Error extracting text with PaddleOCR: {e}")
            raise


def create_ocr_service(languages: str = "eng") -> OCRService:
    """Factory function to create OCR service instance."""
    return OCRService(languages)
