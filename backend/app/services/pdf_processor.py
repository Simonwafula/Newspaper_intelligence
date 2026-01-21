import os
import fitz  # PyMuPDF
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Handles PDF text extraction and page analysis."""
    
    def __init__(self, min_chars_for_native_text: int = 200):
        self.min_chars_for_native_text = min_chars_for_native_text
    
    def extract_page_text(self, doc: fitz.Document, page_num: int) -> Tuple[str, bool]:
        """
        Extract text from a PDF page.
        
        Returns:
            Tuple of (extracted_text, is_scanned)
            is_scanned = True if native text extraction was insufficient
        """
        try:
            page = doc[page_num]
            
            # Try native text extraction first
            text = page.get_text()
            
            # Check if we have enough native text
            if len(text.strip()) >= self.min_chars_for_native_text:
                logger.info(f"Page {page_num + 1}: Using native text extraction ({len(text)} chars)")
                return text, False
            else:
                logger.info(f"Page {page_num + 1}: Native text insufficient ({len(text)} chars), will need OCR")
                return text, True
                
        except Exception as e:
            logger.error(f"Error extracting text from page {page_num + 1}: {e}")
            return "", True
    
    def extract_all_pages(self, file_path: str) -> List[Dict]:
        """
        Extract text from all pages in a PDF.
        
        Returns:
            List of dictionaries with page information
        """
        try:
            doc = fitz.open(file_path)
            pages = []
            
            for page_num in range(len(doc)):
                text, needs_ocr = self.extract_page_text(doc, page_num)
                
                # Get page dimensions
                page = doc[page_num]
                rect = page.rect
                page_info = {
                    'page_number': page_num + 1,
                    'extracted_text': text,
                    'needs_ocr': needs_ocr,
                    'width': rect.width,
                    'height': rect.height,
                    'text_blocks': []
                }
                
                # Extract text blocks with coordinates
                if not needs_ocr:
                    try:
                        blocks = page.get_text("dict")["blocks"]
                        for block in blocks:
                            if "lines" in block:
                                block_text = ""
                                for line in block["lines"]:
                                    line_text = ""
                                    for span in line["spans"]:
                                        line_text += span["text"]
                                    block_text += line_text + "\n"
                                
                                if block_text.strip():
                                    page_info['text_blocks'].append({
                                        'text': block_text.strip(),
                                        'bbox': block['bbox'],  # (x0, y0, x1, y1)
                                        'type': 'text'
                                    })
                    except Exception as e:
                        logger.warning(f"Error extracting text blocks from page {page_num + 1}: {e}")
                
                pages.append(page_info)
            
            doc.close()
            return pages
            
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            raise
    
    def get_page_image(self, file_path: str, page_num: int, dpi: int = 150) -> bytes:
        """
        Render a PDF page as an image for OCR.
        
        Returns:
            Image bytes in PNG format
        """
        try:
            doc = fitz.open(file_path)
            page = doc[page_num]
            
            # Create pixmap with specified DPI
            mat = fitz.Matrix(dpi / 72, dpi / 72)  # Convert DPI to scale matrix
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PNG bytes
            img_bytes = pix.tobytes("png")
            
            doc.close()
            return img_bytes
            
        except Exception as e:
            logger.error(f"Error rendering page {page_num + 1} as image: {e}")
            raise
    
    def get_page_count(self, file_path: str) -> int:
        """Get the number of pages in a PDF."""
        try:
            doc = fitz.open(file_path)
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            logger.error(f"Error getting page count for {file_path}: {e}")
            raise


def create_pdf_processor(min_chars_for_native_text: int = 200) -> PDFProcessor:
    """Factory function to create PDFProcessor instance."""
    return PDFProcessor(min_chars_for_native_text)