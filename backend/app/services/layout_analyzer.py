import logging
import re

from .classifieds_intelligence import create_classifieds_intelligence

logger = logging.getLogger(__name__)

CONTACT_RE = re.compile(r"(\+?\d{1,3}[\s\-])?(?:\(?\d{2,4}\)?[\s\-])?\d{3,4}[\s\-]\d{3,4}")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
URL_RE = re.compile(r"(https?://|www\.)", re.IGNORECASE)
PRICE_RE = re.compile(r"\b(KSH|KES|USD|EUR|GBP|SHS|SH)\b|\$\s?\d|€\s?\d", re.IGNORECASE)
ACTION_RE = re.compile(r"\b(apply|send|call|contact|email|dial|sms|whatsapp)\b", re.IGNORECASE)


class LayoutAnalyzer:
    """Analyzes PDF layout to extract headlines, stories, and classifieds."""

    def __init__(self):
        # Initialize classifieds intelligence
        self.classifieds_service = create_classifieds_intelligence()

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

    def detect_headlines(self, text_blocks: list[dict]) -> list[dict]:
        """
        Detect headlines from text blocks.

        Uses heuristics: short text, likely at top of page, title case or all caps.
        """
        headlines = []

        font_sizes = []
        for block in text_blocks:
            font_size = block.get("font_size")
            if isinstance(font_size, (int, float)) and font_size > 0:
                font_sizes.append(font_size)
                continue
            bbox = block.get("bbox") or [0, 0, 0, 0]
            height = float(bbox[3]) - float(bbox[1])
            line_count = max(1, block.get("text", "").count("\n") + 1)
            approx_size = height / line_count if line_count else 0.0
            if approx_size > 0:
                font_sizes.append(approx_size)
        median_font = 0.0
        if font_sizes:
            font_sizes.sort()
            mid = len(font_sizes) // 2
            median_font = font_sizes[mid] if len(font_sizes) % 2 else (font_sizes[mid - 1] + font_sizes[mid]) / 2

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
                bbox = list(block.get('bbox', [0, 0, 0, 0]))
                y_position = bbox[1]  # y0 coordinate
                is_near_top = y_position < 200  # Arbitrary threshold

                # Heuristic 4: Font-based (larger font is more likely a headline)
                font_size = block.get('font_size')
                if not isinstance(font_size, (int, float)) or font_size <= 0:
                    height = bbox[3] - bbox[1]
                    line_count = max(1, text.count("\n") + 1)
                    font_size = height / line_count if line_count else 0
                is_large_font = font_size > 14  # Typical body font is ~10-12pt
                if median_font:
                    is_large_font = font_size >= max(14, median_font * 1.4)

                # Heuristic 5: Contains headline-like words
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
                if is_large_font:
                    score += 4  # Strong indicator
                if has_indicator:
                    score += 2

                # Consider it a headline if score is high enough
                if score >= 2:
                    headlines.append({
                        'text': text,
                        'bbox': bbox,
                        'block_index': i,
                        'score': score,
                        'column': block.get('column'),
                    })

        # Sort headlines by score (highest first)
        headlines.sort(key=lambda x: x['score'], reverse=True)

        return headlines

    def classify_text_block(self, text: str) -> tuple[str, str | None]:
        """
        Classify a text block as STORY, AD, or CLASSIFIED with subtype.

        Returns:
            Tuple of (item_type, subtype)
        """
        text_upper = text.upper()
        text_len = len(text)
        word_count = len(text.split())
        has_contact = bool(CONTACT_RE.search(text) or EMAIL_RE.search(text) or URL_RE.search(text))
        has_price = bool(PRICE_RE.search(text))
        has_action = bool(ACTION_RE.search(text))
        sentence_count = len(re.findall(r"[.!?]", text))

        def looks_like_story() -> bool:
            if word_count >= 80 and sentence_count >= 3 and not (has_contact or has_price or has_action):
                return True
            return False

        # Check for classified patterns
        for subtype, patterns in self.classified_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_upper, re.IGNORECASE):
                    if looks_like_story():
                        return 'STORY', None
                    if subtype == 'PROPERTY' and not (has_contact or has_price or has_action or word_count <= 40):
                        return 'STORY', None
                    if subtype == 'JOB' and not (has_contact or has_action or word_count <= 60):
                        return 'STORY', None
                    if subtype == 'NOTICE' and not (has_contact or word_count <= 60):
                        return 'STORY', None
                    if subtype in {'TENDER', 'AUCTION'} and not (has_contact or has_action or word_count <= 80):
                        return 'STORY', None
                    if word_count > 120 and not (has_contact or has_price or has_action):
                        return 'STORY', None
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
            if looks_like_story():
                return 'STORY', None
            if word_count > 120 and not (has_contact or has_price):
                return 'STORY', None
            return 'AD', 'ADVERTISEMENT'

        # Default to story
        return 'STORY', None

    def extract_items_from_page(self, text_blocks: list[dict], headlines: list[dict]) -> list[dict]:
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
            headline_col = headline.get('column')
            headline_bbox = list(headline.get('bbox') or [0, 0, 0, 0])

            # Find text blocks that come after this headline
            grouped_text = [headline['text']]
            grouped_bbox = list(headline['bbox']) if headline.get('bbox') else [0, 0, 0, 0]
            used_blocks.add(headline_idx)

            # Look for subsequent blocks until next headline or end of page
            for j in range(headline_idx + 1, len(text_blocks)):
                if j in used_blocks:
                    continue

                block = text_blocks[j]
                block_text = block['text'].strip()

                # Stop if we hit another headline
                if any(h['block_index'] == j and h.get('column') == headline_col for h in headlines):
                    break
                if headline_col is not None and block.get('column') != headline_col:
                    continue
                if block.get('bbox') and headline_bbox and block['bbox'][1] < headline_bbox[1]:
                    continue

                # Include this block in the current item
                grouped_text.append(block_text)
                used_blocks.add(j)

                # Expand bounding box to include this block
                bbox = list(block.get('bbox', [0, 0, 0, 0]))
                if grouped_bbox:
                    grouped_bbox[0] = min(grouped_bbox[0], bbox[0])  # left
                    grouped_bbox[1] = min(grouped_bbox[1], bbox[1])  # top
                    grouped_bbox[2] = max(grouped_bbox[2], bbox[2])  # right
                    grouped_bbox[3] = max(grouped_bbox[3], bbox[3])  # bottom

            # Create item from grouped text
            full_text = '\n'.join(grouped_text)
            item_type, subtype = self.classify_text_block(full_text)

            # Extract structured data for classifieds
            structured_data = {}
            if item_type == 'CLASSIFIED' and subtype:
                structured_data = self.classifieds_service.process_classified(full_text, subtype)

            items.append({
                'title': full_text,
                'text': full_text,
                'item_type': item_type,
                'subtype': subtype,
                'bbox_json': grouped_bbox,
                'confidence': headline['score'],
                'contact_info_json': structured_data.get('contact_info'),
                'price_info_json': structured_data.get('price_info'),
                'date_info_json': structured_data.get('date_info'),
                'location_info_json': structured_data.get('location_info'),
                'classification_details_json': structured_data.get('classification_details'),
                'structured_data': structured_data if item_type == 'CLASSIFIED' and subtype else None
            })

        # Process remaining standalone blocks
        for i, block in enumerate(text_blocks):
            if i in used_blocks:
                continue

            text = block['text'].strip()
            if not text:
                continue

            item_type, subtype = self.classify_text_block(text)

            # Extract structured data for classifieds
            structured_data = {}
            if item_type == 'CLASSIFIED' and subtype:
                structured_data = self.classifieds_service.process_classified(text, subtype)

            items.append({
                'title': text[:100] + ('...' if len(text) > 100 else ''),  # First 100 chars as title
                'text': text,
                'item_type': item_type,
                'subtype': subtype,
                'bbox_json': list(block.get('bbox', [0, 0, 0, 0])),
                'confidence': 1.0,
                'contact_info_json': structured_data.get('contact_info'),
                'price_info_json': structured_data.get('price_info'),
                'date_info_json': structured_data.get('date_info'),
                'location_info_json': structured_data.get('location_info'),
                'classification_details_json': structured_data.get('classification_details'),
                'structured_data': structured_data if item_type == 'CLASSIFIED' and subtype else None
            })

        return items

    def _estimate_columns(self, text_blocks: list[dict], page_width: float) -> list[float]:
        x_positions = sorted(
            {float(block.get('bbox', [0, 0, 0, 0])[0]) for block in text_blocks if block.get('bbox')}
        )
        if not x_positions or page_width <= 0:
            return [0.0]
        gaps = []
        for i in range(1, len(x_positions)):
            gap = x_positions[i] - x_positions[i - 1]
            if gap > page_width * 0.08:
                gaps.append((x_positions[i - 1], x_positions[i], gap))
        if not gaps:
            return [0.0]
        # Create column boundaries based on significant gaps (max 3 splits -> 4 columns)
        gaps.sort(key=lambda g: g[2], reverse=True)
        splits = sorted([g[1] for g in gaps[:3]])
        columns = [0.0] + splits
        return columns

    def _order_blocks(self, text_blocks: list[dict], page_width: float) -> list[dict]:
        if not text_blocks:
            return []
        blocks = [dict(block) for block in text_blocks]
        columns = self._assign_columns(blocks)
        ordered: list[dict] = []
        for _, col_blocks in columns:
            col_blocks.sort(key=lambda b: float((b.get('bbox') or [0, 0, 0, 0])[1]))
            ordered.extend(self._merge_column_blocks(col_blocks))
        return ordered

    def _assign_columns(self, text_blocks: list[dict], x_overlap_threshold: float = 0.6) -> list[tuple[float, list[dict]]]:
        columns: list[list[dict]] = []
        col_boxes: list[list[float]] = []
        for block in sorted(text_blocks, key=lambda b: (float((b.get('bbox') or [0, 0, 0, 0])[0]), float((b.get('bbox') or [0, 0, 0, 0])[1]))):
            bbox = list(block.get('bbox') or [0, 0, 0, 0])
            placed = False
            for idx, col_box in enumerate(col_boxes):
                if self._x_overlap_ratio(bbox, col_box) >= x_overlap_threshold:
                    columns[idx].append(block)
                    col_boxes[idx] = self._bbox_union(col_box, bbox)
                    block['column'] = idx
                    placed = True
                    break
            if not placed:
                block['column'] = len(columns)
                columns.append([block])
                col_boxes.append(bbox)
        ordered_columns = sorted(
            [(col_boxes[i][0], columns[i]) for i in range(len(columns))],
            key=lambda item: item[0],
        )
        for col_idx, (_, col_blocks) in enumerate(ordered_columns):
            for block in col_blocks:
                block['column'] = col_idx
        return ordered_columns

    def _merge_column_blocks(self, blocks: list[dict]) -> list[dict]:
        if not blocks:
            return []
        merged: list[dict] = []
        for block in blocks:
            if not merged:
                merged.append(block)
                continue
            prev = merged[-1]
            if not self._can_merge(prev, block):
                merged.append(block)
                continue
            merged[-1] = self._merge_blocks(prev, block)
        return merged

    def _can_merge(self, a: dict, b: dict, gap_multiplier: float = 1.5) -> bool:
        if a.get('column') != b.get('column'):
            return False
        if (a.get('type') or 'text') not in {'text', 'ocr_text'}:
            return False
        if (b.get('type') or 'text') not in {'text', 'ocr_text'}:
            return False
        a_bbox = a.get('bbox') or [0, 0, 0, 0]
        b_bbox = b.get('bbox') or [0, 0, 0, 0]
        gap = float(b_bbox[1]) - float(a_bbox[3])
        line_height = self._estimate_line_height(a)
        if gap > gap_multiplier * line_height:
            return False
        if self._x_overlap_ratio(a_bbox, b_bbox) < 0.7:
            return False
        return True

    def _estimate_line_height(self, block: dict) -> float:
        font_size = block.get('font_size')
        if isinstance(font_size, (int, float)) and font_size > 0:
            return float(font_size)
        bbox = block.get('bbox') or [0, 0, 0, 0]
        height = float(bbox[3]) - float(bbox[1])
        lines = max(1, block.get("text", "").count("\n") + 1)
        approx = height / lines if lines else 0.0
        return max(10.0, min(40.0, approx))

    def _merge_blocks(self, a: dict, b: dict) -> dict:
        bbox = self._bbox_union(a.get('bbox') or [0, 0, 0, 0], b.get('bbox') or [0, 0, 0, 0])
        text_a = a.get('text', '').strip()
        text_b = b.get('text', '').strip()
        merged_text = (text_a + "\n" + text_b).strip() if text_a and text_b else (text_a or text_b)
        font_size = max(a.get('font_size') or 0, b.get('font_size') or 0)
        merged = dict(a)
        merged.update({
            'text': merged_text,
            'bbox': bbox,
            'font_size': font_size or a.get('font_size') or b.get('font_size'),
        })
        return merged

    def _x_overlap_ratio(self, a: list[float], b: list[float]) -> float:
        inter_x1 = max(float(a[0]), float(b[0]))
        inter_x2 = min(float(a[2]), float(b[2]))
        inter = max(0.0, inter_x2 - inter_x1)
        if inter == 0:
            return 0.0
        width = min(float(a[2]) - float(a[0]), float(b[2]) - float(b[0]))
        return inter / width if width else 0.0

    def _bbox_union(self, a: list[float], b: list[float]) -> list[float]:
        return [
            min(float(a[0]), float(b[0])),
            min(float(a[1]), float(b[1])),
            max(float(a[2]), float(b[2])),
            max(float(a[3]), float(b[3])),
        ]

    def analyze_page(self, page_info: dict) -> dict:
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

        page_width = float(page_info.get('width') or 0)
        ordered_blocks = self._order_blocks(text_blocks, page_width)

        # Detect headlines
        headlines = self.detect_headlines(ordered_blocks)

        # Extract items
        items = self.extract_items_from_page(ordered_blocks, headlines)

        # Update page info
        page_info['headlines'] = headlines
        page_info['extracted_items'] = items
        page_info['num_items'] = len(items)
        page_info['text_blocks'] = ordered_blocks

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
