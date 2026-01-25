import logging

try:
    import io

    import pytesseract
from PIL import Image

from app.settings import settings
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("Tesseract OCR not available. Install with: pip install pytesseract pillow")

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

    def extract_text_with_boxes(self, image_bytes: bytes) -> dict:
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

            # Get detailed OCR data with bounding boxes
            data = pytesseract.image_to_data(image, lang=self.languages, output_type=pytesseract.Output.DICT)

            # Process the data to extract text blocks
            text_blocks = []
            current_text = ""
            current_bbox = None

            for i in range(len(data['text'])):
                text = data['text'][i].strip()
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

                conf = int(data['conf'][i])
                if conf > 30:  # Only include text with confidence > 30%
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]

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
            full_text = " ".join([block['text'] for block in text_blocks])

            return {
                'text': full_text,
                'text_blocks': text_blocks
            }

        except Exception as e:
            logger.error(f"Error extracting OCR text with boxes: {e}")
            # Fallback to simple text extraction
            return {
                'text': self.extract_text_from_image(image_bytes),
                'text_blocks': []
            }

    def is_available(self) -> bool:
        """Check if OCR service is available."""
        return self.available


def create_ocr_service(languages: str = "eng") -> OCRService:
    """Factory function to create OCR service instance."""
    return OCRService(languages)
