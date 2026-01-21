import re
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class LayoutAnalyzer:
    """Analyzes PDF layout to extract headlines, stories, and classifieds."""
    
    def __init__(self):
        # Patterns for classified ad detection
        self.classified_patterns = {
            'TENDER': [
                r'\bTENDER\b', r'\bPREQUALIFICATION\b', r'\bREQUEST FOR PROPOSAL\b',
                r'\bRFP\b', r'\bRFQ\b', r'\bTENDER NOTICE\b'
            ],
            'JOB': [
                r'\bVACANCY\b', r'\bCAREER\b', r'\bJOB\b', r'\bAPPLICATIONS INVITED\b',
                r'\bEMPLOYMENT\b', r'\bPOSITION\b', r'\bHIRING\b'
            ],
            'AUCTION': [
                r'\bAUCTION\b', r'\bREPOSSESSED\b', r'\bMOTOR VEHICLE AUCTION\b',
                r'\bPROPERTY AUCTION\b', r'\bPUBLIC AUCTION\b'
            ],
            'NOTICE': [
                r'\bPUBLIC NOTICE\b', r'\bLOST\b', r'\bOBITUARY\b', r'\bDECEASED\b',
                r'\bNOTICE\b', r'\bIN MEMORIAM\b', r'\bDEATH NOTICE\b'
            ],
            'PROPERTY': [
                r'\bTO LET\b', r'\bFOR SALE\b', r'\bPLOT\b', r'\bAPARTMENT\b',
                r'\bHOUSE\b', r'\bLAND\b', r'\bREAL ESTATE\b', r'\bRENT\b'
            ]
        }
    
    def detect_headlines(self, text_blocks: List[Dict]) -> List[Dict]:
        """
        Detect headlines from text blocks.
        
        Uses heuristics: short text, likely at top of page, title case or all caps.
        """
        headlines = []
        
        for i, block in enumerate(text_blocks):
            text = block['text'].strip()
            if not text or len(text) < 5:
                continue
            
            # Skip very long blocks (likely not headlines)
            if len(text) > 200:
                continue
            
            # Heuristic 1: Short text (typical headlines)
            if len(text) < 100:
                # Heuristic 2: Title case or all caps
                words = text.split()
                title_case_words = sum(1 for word in words if word[0].isupper() if word.isalpha())
                title_case_ratio = title_case_words / len(words) if words else 0
                
                all_caps = text.isupper()
                
                # Heuristic 3: Position-based (blocks near top are more likely headlines)
                bbox = block.get('bbox', [0, 0, 0, 0])
                y_position = bbox[1]  # y0 coordinate
                is_near_top = y_position < 200  # Arbitrary threshold
                
                # Heuristic 4: Contains headline-like words
                headline_indicators = [
                    'breaking', 'exclusive', 'update', 'news', 'report',
                    'analysis', 'feature', 'opinion', 'editorial'
                ]
                has_indicator = any(indicator in text.lower() for indicator in headline_indicators)
                
                # Score the block as a headline
                score = 0
                if title_case_ratio > 0.6:
                    score += 2
                if all_caps:
                    score += 3
                if is_near_top:
                    score += 1
                if has_indicator:
                    score += 2
                
                # Consider it a headline if score is high enough
                if score >= 2:
                    headlines.append({
                        'text': text,
                        'bbox': bbox,
                        'block_index': i,
                        'score': score
                    })
        
        # Sort headlines by score (highest first)
        headlines.sort(key=lambda x: x['score'], reverse=True)
        
        return headlines
    
    def classify_text_block(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Classify a text block as STORY, AD, or CLASSIFIED with subtype.
        
        Returns:
            Tuple of (item_type, subtype)
        """
        text_upper = text.upper()
        
        # Check for classified patterns
        for subtype, patterns in self.classified_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_upper, re.IGNORECASE):
                    return 'CLASSIFIED', subtype
        
        # Check for general advertisement indicators
        ad_indicators = [
            r'\bAD\b', r'\bADVERTISEMENT\b', r'\bPROMOTION\b', r'\bOFFER\b',
            r'\bDISCOUNT\b', r'\bSALE\b', r'\bSPECIAL\b', r'\bLIMITED\b',
            r'\bCALL\b.*\bNOW\b', r'\bCONTACT\b', r'\bPHONE\b', r'\bEMAIL\b',
            r'\bWEBSITE\b', r'\bWWW\.', r'\b\.COM\b'
        ]
        
        ad_score = sum(1 for pattern in ad_indicators if re.search(pattern, text_upper))
        if ad_score >= 2:  # Require at least 2 ad indicators
            return 'AD', 'ADVERTISEMENT'
        
        # Default to story
        return 'STORY', None
    
    def extract_items_from_page(self, text_blocks: List[Dict], headlines: List[Dict]) -> List[Dict]:
        """
        Extract items (stories, ads, classifieds) from text blocks.
        
        Groups text blocks under headlines and classifies them.
        """
        if not text_blocks:
            return []
        
        items = []
        used_blocks = set()
        
        # Process headline-based groupings first
        for headline in headlines:
            headline_idx = headline['block_index']
            if headline_idx in used_blocks:
                continue
            
            # Find text blocks that come after this headline
            grouped_text = [headline['text']]
            grouped_bbox = headline['bbox'].copy()
            used_blocks.add(headline_idx)
            
            # Look for subsequent blocks until next headline or end of page
            for j in range(headline_idx + 1, len(text_blocks)):
                if j in used_blocks:
                    continue
                
                block = text_blocks[j]
                block_text = block['text'].strip()
                
                # Stop if we hit another headline
                if any(h['block_index'] == j for h in headlines):
                    break
                
                # Include this block in the current item
                grouped_text.append(block_text)
                used_blocks.add(j)
                
                # Expand bounding box to include this block
                bbox = block.get('bbox', [0, 0, 0, 0])
                if grouped_bbox:
                    grouped_bbox[0] = min(grouped_bbox[0], bbox[0])  # left
                    grouped_bbox[1] = min(grouped_bbox[1], bbox[1])  # top
                    grouped_bbox[2] = max(grouped_bbox[2], bbox[2])  # right
                    grouped_bbox[3] = max(grouped_bbox[3], bbox[3])  # bottom
            
            # Create item from grouped text
            full_text = '\n'.join(grouped_text)
            item_type, subtype = self.classify_text_block(full_text)
            
            items.append({
                'title': headline['text'],
                'text': full_text,
                'item_type': item_type,
                'subtype': subtype,
                'bbox_json': grouped_bbox,
                'confidence': headline['score']
            })
        
        # Process remaining standalone blocks
        for i, block in enumerate(text_blocks):
            if i in used_blocks:
                continue
            
            text = block['text'].strip()
            if not text:
                continue
            
            item_type, subtype = self.classify_text_block(text)
            
            items.append({
                'title': text[:100] + ('...' if len(text) > 100 else ''),  # First 100 chars as title
                'text': text,
                'item_type': item_type,
                'subtype': subtype,
                'bbox_json': block.get('bbox'),
                'confidence': 1.0
            })
        
        return items
    
    def analyze_page(self, page_info: Dict) -> Dict:
        """
        Analyze a page to extract structured items.
        
        Args:
            page_info: Dictionary with page information including text blocks
            
        Returns:
            Updated page info with extracted items
        """
        text_blocks = page_info.get('text_blocks', [])
        if not text_blocks and page_info.get('extracted_text'):
            # Create a single block from the extracted text
            text_blocks = [{
                'text': page_info['extracted_text'],
                'bbox': [0, 0, 0, 0],  # Default bbox
                'type': 'text'
            }]
        
        # Detect headlines
        headlines = self.detect_headlines(text_blocks)
        
        # Extract items
        items = self.extract_items_from_page(text_blocks, headlines)
        
        # Update page info
        page_info['headlines'] = headlines
        page_info['extracted_items'] = items
        page_info['num_items'] = len(items)
        
        # Add classification summary
        item_counts = {}
        for item in items:
            item_type = item['item_type']
            item_counts[item_type] = item_counts.get(item_type, 0) + 1
        
        page_info['item_summary'] = item_counts
        
        return page_info


def create_layout_analyzer() -> LayoutAnalyzer:
    """Factory function to create LayoutAnalyzer instance."""
    return LayoutAnalyzer()