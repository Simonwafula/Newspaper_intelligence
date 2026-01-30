"""
Salience Service - Scan mode attention scoring and Dive mode helpers.

This service provides:
- Salience scoring for scan mode (attention ranking)
- Lede text extraction (first N sentences)
- Key facts extraction (who/what/where/when + numbers + dates)
"""

import logging
import re
from typing import Any, Optional

from app.settings import settings

logger = logging.getLogger(__name__)

# Regex patterns for key facts extraction
PERSON_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
DATE_RE = re.compile(
    r"\b(?:\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}|"  # 01/02/2024
    r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|"  # 15 Jan 2024
    r"yesterday|today|tomorrow)\b",
    re.IGNORECASE
)
NUMBER_RE = re.compile(r"\b\d+(?:,\d{3})*(?:\.\d+)?(?:K|M|B|T|thousand|million|billion|trillion)?\b")
LOCATION_RE = re.compile(
    r"\b(?:[A-Z][a-z]+(?:,\s*[A-Z][a-z]+)+)\b|"  # City, Country
    r"(?:Nairobi|Mombasa|Kisumu|Nakuru|Eldoret|Garissa|Kakuma|Lodwar)\b"  # Kenyan cities
)
SENTENCE_END_RE = re.compile(r"[.!?]+\s+|[.!?]$")


class SalienceService:
    """Service for salience scoring and dive mode helpers."""

    def __init__(self):
        self.enabled = settings.salience_enabled
        self.lede_sentences = settings.salience_lede_sentences
        self.front_page_boost = settings.salience_front_page_boost

    def compute_salience_score(
        self,
        item_text: str,
        title: Optional[str] = None,
        blocks_json: Optional[list[dict]] = None,
        page_number: Optional[int] = None,
        item_type: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Compute salience score (0-1) for scan mode attention ranking.

        Args:
            item_text: Full text of the item
            title: Item title (headline)
            blocks_json: Block-level data for font size/area
            page_number: Page number (for front page boost)
            item_type: Item type (STORY, AD, CLASSIFIED)

        Returns:
            Dictionary with:
                - salience_score: float (0-1)
                - salience_reasons: list of reasons explaining score
                - signals: dict of individual signal scores
        """
        result = {
            'salience_score': 0.0,
            'salience_reasons': [],
            'signals': {}
        }

        if not item_text or not item_text.strip():
            return result

        # Extract individual signals
        signals = {}

        # Signal 1: Headline font size / bbox area
        signals['headline_importance'] = self._compute_headline_importance(title, blocks_json)

        # Signal 2: Image presence and size
        signals['image_importance'] = self._compute_image_importance(blocks_json)

        # Signal 3: Placement (top-of-page)
        signals['placement_score'] = self._compute_placement_score(blocks_json)

        # Signal 4: Story length (longer = more important, but not too long)
        signals['length_score'] = self._compute_length_score(item_text)

        # Signal 5: Section cues / keywords
        signals['section_score'] = self._compute_section_score(title, item_text)

        # Signal 6: Front page boost
        signals['front_page_boost'] = self._compute_front_page_boost(page_number)

        # Signal 7: Item type (STORY > CLASSIFIED > AD)
        signals['type_boost'] = self._compute_type_boost(item_type)

        # Compute weighted score
        result['salience_score'] = self._combine_salience_signals(signals)

        # Generate reasons
        result['salience_reasons'] = self._generate_salience_reasons(signals, result['salience_score'])
        result['signals'] = signals

        return result

    def extract_lede_text(
        self,
        text: str,
        num_sentences: Optional[int] = None
    ) -> str:
        """
        Extract lede text (first N sentences) for dive mode.

        Args:
            text: Full text content
            num_sentences: Number of sentences to extract (defaults to setting)

        Returns:
            First N sentences as clean, deterministric string
        """
        if not text or not text.strip():
            return ""

        num_sentences = num_sentences or self.lede_sentences

        # Split into sentences using sentence_end_re
        sentences = []
        for match in SENTENCE_END_RE.finditer(text):
            sentence_end = match.end()
            sentences.append(text[:sentence_end].strip())
            text = text[sentence_end:]

        # Handle remaining text if no sentence endings found
        if not sentences and text:
            sentences.append(text.strip())

        # Take first N sentences
        lede_sentences = sentences[:num_sentences]

        return " ".join(lede_sentences)

    def extract_key_facts(
        self,
        text: str,
        title: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Extract key facts (who/what/where/when + numbers + dates).

        Args:
            text: Full text content
            title: Item title (headline)

        Returns:
            Dictionary with:
                - who: list of potential people/organizations
                - what: summary of what the story is about
                - where: list of locations
                - when: list of dates
                - numbers: list of numeric values
                - metadata_json: complete structured facts
        """
        result = {
            'who': [],
            'what': None,
            'where': [],
            'when': [],
            'numbers': [],
            'metadata_json': {}
        }

        if not text or not text.strip():
            return result

        full_text = (title or "") + "\n" + text if title else text

        # Extract people/organizations (who)
        result['who'] = self._extract_persons(full_text)

        # Extract locations (where)
        result['where'] = self._extract_locations(full_text)

        # Extract dates (when)
        result['when'] = self._extract_dates(full_text)

        # Extract numbers (key figures)
        result['numbers'] = self._extract_numbers(full_text)

        # Generate "what" summary
        result['what'] = self._generate_what_summary(full_text)

        # Store complete metadata
        result['metadata_json'] = {
            'who_count': len(result['who']),
            'where_count': len(result['where']),
            'when_count': len(result['when']),
            'numbers_count': len(result['numbers']),
            'text_length': len(full_text),
        }

        return result

    def _compute_headline_importance(
        self,
        title: Optional[str],
        blocks_json: Optional[list[dict]]
    ) -> float:
        """Compute score based on headline font size and bbox area."""
        if not title:
            return 0.0

        score = 0.0

        # Title length matters (shorter = more headline-like)
        words = title.split()
        if 3 <= len(words) <= 15:
            score += 0.7
        elif len(words) < 3:
            score += 0.5
        elif len(words) <= 25:
            score += 0.3

        # Check block-level font size if available
        if blocks_json:
            title_blocks = [
                block for block in blocks_json
                if 'headline' in (block.get('type', '') or '').lower() or
                   'title' in (block.get('type', '') or '').lower()
            ]
            if title_blocks:
                # Use font size from first title block
                font_size = title_blocks[0].get('font_size')
                if isinstance(font_size, (int, float)) and font_size > 0:
                    # Larger font = higher salience
                    if font_size >= 20:
                        score = max(score, 1.0)
                    elif font_size >= 16:
                        score = max(score, 0.8)
                    elif font_size >= 14:
                        score = max(score, 0.6)

        return min(score, 1.0)

    def _compute_image_importance(self, blocks_json: Optional[list[dict]]) -> float:
        """Compute score based on image presence and size."""
        if not blocks_json:
            return 0.0

        image_blocks = [
            block for block in blocks_json
            if 'image' in (block.get('type', '') or '').lower() or
               'figure' in (block.get('type', '') or '').lower()
        ]

        if not image_blocks:
            return 0.0

        # Score based on number and size of images
        num_images = len(image_blocks)
        total_image_area = 0.0
        total_area = 0.0

        for block in blocks_json:
            bbox = block.get('bbox')
            if bbox and len(bbox) == 4:
                width = float(bbox[2]) - float(bbox[0])
                height = float(bbox[3]) - float(bbox[1])
                area = width * height
                total_area += area

                if 'image' in (block.get('type', '') or '').lower():
                    total_image_area += area

        if total_area == 0:
            return 0.0

        # More images = higher salience (up to a point)
        if 1 <= num_images <= 3:
            score = 0.8
        elif num_images > 3:
            score = 1.0
        else:
            score = 0.3

        # Image area ratio
        area_ratio = total_image_area / total_area
        if area_ratio > 0.3:
            score = min(score + 0.2, 1.0)

        return score

    def _compute_placement_score(self, blocks_json: Optional[list[dict]]) -> float:
        """Compute score based on vertical placement on page."""
        if not blocks_json:
            return 0.5

        # Get min y-position (top of first block)
        min_y = None
        for block in blocks_json:
            bbox = block.get('bbox')
            if bbox and len(bbox) >= 2:
                y = float(bbox[1])  # y0 is top
                if min_y is None or y < min_y:
                    min_y = y

        if min_y is None:
            return 0.5

        # Assume typical page height is ~1000 units (arbitrary)
        # Higher score for items higher on the page (smaller y value)
        if min_y < 200:
            return 1.0
        elif min_y < 400:
            return 0.8
        elif min_y < 600:
            return 0.5
        else:
            return 0.2

    def _compute_length_score(self, text: str) -> float:
        """Compute score based on text length (moderate is best)."""
        word_count = len(text.split())

        # Sweet spot: 200-600 words
        if 200 <= word_count <= 600:
            return 1.0
        elif 100 <= word_count < 200:
            return 0.7
        elif 600 < word_count <= 1000:
            return 0.6
        elif word_count < 100:
            return 0.3
        elif word_count > 1000:
            return 0.2  # Too long = likely not a focused story
        else:
            return 0.5

    def _compute_section_score(
        self,
        title: Optional[str],
        text: str
    ) -> float:
        """Compute score based on section cues and keywords."""
        full_text = (title or "") + " " + text
        text_lower = full_text.lower()

        # High-salience section keywords
        high_salience_keywords = [
            'breaking', 'exclusive', 'urgent', 'alert',
            'government', 'president', 'minister', 'parliament',
            'election', 'politics', 'economy', 'business'
        ]

        matches = sum(1 for kw in high_salience_keywords if kw in text_lower)

        # More matches = higher score
        if matches >= 2:
            return 1.0
        elif matches == 1:
            return 0.7
        else:
            return 0.0

    def _compute_front_page_boost(self, page_number: Optional[int]) -> float:
        """Compute front page boost."""
        if page_number is None:
            return 0.0
        if page_number == 1:
            return self.front_page_boost  # Default: 0.2
        else:
            return 0.0

    def _compute_type_boost(self, item_type: Optional[str]) -> float:
        """Compute score boost based on item type."""
        if item_type == 'STORY':
            return 0.2  # Stories are most salient
        elif item_type == 'CLASSIFIED':
            return 0.1  # Classifieds somewhat salient
        elif item_type == 'AD':
            return 0.0  # Ads least salient
        else:
            return 0.0

    def _combine_salience_signals(self, signals: dict[str, float]) -> float:
        """
        Combine individual salience signals into final score.

        Signal weights:
        - Headline importance: 25%
        - Image importance: 20%
        - Placement: 15%
        - Length: 15%
        - Section: 15%
        - Front page boost: 5%
        - Type boost: 5%

        Returns:
            Combined score between 0 and 1
        """
        weights = {
            'headline_importance': 0.25,
            'image_importance': 0.20,
            'placement_score': 0.15,
            'length_score': 0.15,
            'section_score': 0.15,
            'front_page_boost': 0.05,
            'type_boost': 0.05,
        }

        total_score = 0.0
        for signal_name, weight in weights.items():
            signal_value = signals.get(signal_name, 0.0)
            total_score += signal_value * weight

        return max(0.0, min(1.0, total_score))

    def _generate_salience_reasons(self, signals: dict[str, float], final_score: float) -> list[str]:
        """Generate human-readable reasons for salience score."""
        reasons = []

        if signals.get('headline_importance', 0) > 0.7:
            reasons.append("Strong headline (short, attention-grabbing)")

        if signals.get('image_importance', 0) > 0.5:
            reasons.append("Includes prominent images")

        if signals.get('placement_score', 0) > 0.7:
            reasons.append("Placed near top of page")

        if signals.get('length_score', 0) > 0.8:
            reasons.append("Optimal story length (well-developed)")

        if signals.get('section_score', 0) > 0.5:
            reasons.append("Contains high-salience section keywords")

        if signals.get('front_page_boost', 0) > 0:
            reasons.append("Front page placement")

        if signals.get('type_boost', 0) > 0.1:
            reasons.append("News story (high priority)")

        return reasons

    def _extract_persons(self, text: str) -> list[str]:
        """Extract potential people/organizations using regex."""
        # Use simple regex-based extraction
        # In production, would use NER model (spacy/stanza)
        persons = []
        for match in PERSON_RE.finditer(text):
            person = match.group(1)
            if person not in persons:
                persons.append(person)
        return persons[:10]  # Top 10 unique persons

    def _extract_locations(self, text: str) -> list[str]:
        """Extract locations using regex."""
        locations = []
        for match in LOCATION_RE.finditer(text):
            location = match.group(0)
            if location not in locations:
                locations.append(location)
        return locations[:10]  # Top 10 unique locations

    def _extract_dates(self, text: str) -> list[str]:
        """Extract dates using regex."""
        dates = []
        for match in DATE_RE.finditer(text):
            date = match.group(0)
            if date not in dates:
                dates.append(date)
        return dates[:5]  # Top 5 unique dates

    def _extract_numbers(self, text: str) -> list[str]:
        """Extract numeric values using regex."""
        numbers = []
        for match in NUMBER_RE.finditer(text):
            number = match.group(0)
            if number not in numbers:
                numbers.append(number)
        return numbers[:10]  # Top 10 unique numbers

    def _generate_what_summary(self, text: str) -> Optional[str]:
        """Generate summary of what the story is about."""
        # Simple approach: take first sentence up to 100 chars
        sentences = []
        for match in SENTENCE_END_RE.finditer(text):
            sentence_end = match.end()
            sentence = text[:sentence_end].strip()
            sentences.append(sentence)
            text = text[sentence_end:]

        if sentences:
            first_sentence = sentences[0]
            if len(first_sentence) <= 100:
                return first_sentence
            else:
                return first_sentence[:97] + "..."
        else:
            return None


def create_salience_service() -> SalienceService:
    """Factory function to create SalienceService instance."""
    return SalienceService()
