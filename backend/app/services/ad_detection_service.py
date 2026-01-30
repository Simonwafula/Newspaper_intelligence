"""
Ad Detection Service - Multi-signal AD classifier.

This service provides:
- Multi-signal ad candidate scoring (image ratio, CTA keywords, contact density, etc.)
- Explainable ad detection with reasons
- Configurable thresholds and keyword lists
"""

import logging
import re
from typing import Any, Optional

from app.settings import settings

logger = logging.getLogger(__name__)

# Regex patterns for ad detection
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s\-])?(?:\(?\d{2,4}\)?[\s\-])?\d{3,4}[\s\-]\d{3,4}")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PRICE_RE = re.compile(r"\b(KSh|KES|USD|EUR|GBP|SHS|SH)\b|\$\s?\d|€\s?\d|\/\=", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")


class AdDetectionService:
    """Service for multi-signal advertisement detection."""

    def __init__(self):
        self.enabled = settings.ad_detection_enabled
        self.threshold = settings.ad_candidate_threshold

        # Call-to-action keywords (from settings or defaults)
        self.cta_keywords = settings.ad_cta_keywords or [
            "Call", "WhatsApp", "Visit", "Offer", "Discount", "Terms", "Promo",
            "Limited", "Sale", "Buy", "Order", "Book", "Contact", "Phone",
            "Email", "Website", "www", ".com", "Shop", "Store"
        ]

        # Price patterns (from settings or defaults)
        self.price_patterns = settings.ad_price_patterns or [
            "KSh", "KES", "/=", "%", "Sh", "USD", "EUR", "GBP", "$"
        ]

    def compute_ad_candidate_score(
        self,
        item_text: str,
        item_type: Optional[str] = None,
        blocks_json: Optional[list[dict]] = None,
        bbox_json: Optional[list] = None
    ) -> dict[str, Any]:
        """
        Compute ad candidate score and reasons for an item.

        Args:
            item_text: The full text content of the item
            item_type: Current item_type classification (STORY, AD, CLASSIFIED)
            blocks_json: Block-level data for image area calculation
            bbox_json: Bounding box for overall item

        Returns:
            Dictionary with:
                - ad_candidate_score: float (0-1)
                - ad_detection_reasons: list of reasons explaining the score
                - signals: dict of individual signal scores
        """
        result = {
            'ad_candidate_score': 0.0,
            'ad_detection_reasons': [],
            'signals': {}
        }

        if not item_text or not item_text.strip():
            return result

        # Extract individual signals
        signals = {}

        # Signal 1: Image area ratio
        signals['image_area_ratio'] = self._compute_image_area_ratio(blocks_json, bbox_json)

        # Signal 2: CTA keyword density
        signals['cta_keyword_score'] = self._compute_cta_keyword_score(item_text)

        # Signal 3: Contact information density
        signals['contact_density'] = self._compute_contact_density(item_text)

        # Signal 4: Brand-like tokens (uppercase patterns)
        signals['brand_token_score'] = self._compute_brand_token_score(item_text)

        # Signal 5: Price pattern density
        signals['price_density'] = self._compute_price_density(item_text)

        # Signal 6: Text length (shorter text more likely ad)
        signals['length_penalty'] = self._compute_length_penalty(item_text)

        # Signal 7: Layout type boost (if AD block type)
        signals['layout_ad_boost'] = self._compute_layout_ad_boost(blocks_json)

        # Compute weighted score
        result['ad_candidate_score'] = self._combine_signals(signals)

        # Generate reasons
        result['ad_detection_reasons'] = self._generate_reasons(signals, result['ad_candidate_score'])
        result['signals'] = signals

        return result

    def should_classify_as_ad(
        self,
        ad_candidate_score: float,
        detection_reasons: list[str],
        item_type: Optional[str] = None,
        subtype: Optional[str] = None
    ) -> bool:
        """
        Determine if an item should be classified as an AD.

        Args:
            ad_candidate_score: Computed ad candidate score (0-1)
            detection_reasons: List of detection reasons
            item_type: Current item type
            subtype: Current subtype (e.g., JOB, TENDER, NOTICE)

        Returns:
            True if item should be classified as AD, False otherwise
        """
        # If score is below threshold, it's not an ad
        if ad_candidate_score < self.threshold:
            return False

        # Special case: Clear classified subtypes should NOT be mislabeled as ads
        if item_type == 'CLASSIFIED' and subtype in ['JOB', 'TENDER', 'NOTICE', 'AUCTION']:
            # Even if score is high, keep as classified
            logger.info(f"Keeping {item_type}/{subtype} despite ad_score={ad_candidate_score:.3f}")
            return False

        # Check for explicit STORY indicators
        story_indicators = [
            'reported by', 'correspondent', 'news', 'editorial', 'opinion',
            'feature', 'analysis', 'according to'
        ]
        if any(reason.lower() in story_indicators for reason in detection_reasons):
            return False

        return True

    def _compute_image_area_ratio(
        self,
        blocks_json: Optional[list[dict]],
        bbox_json: Optional[list]
    ) -> float:
        """
        Compute ratio of image area to total item area.

        Returns:
            Score between 0 and 1 (higher = more image area)
        """
        if not blocks_json or not bbox_json:
            return 0.0

        # Calculate total item area
        item_width = float(bbox_json[2]) - float(bbox_json[0])
        item_height = float(bbox_json[3]) - float(bbox_json[1])
        if item_width <= 0 or item_height <= 0:
            return 0.0
        total_area = item_width * item_height

        # Sum image block areas
        image_area = 0.0
        for block in blocks_json:
            block_type = (block.get('type', '') or '').lower()
            if 'image' in block_type or 'figure' in block_type:
                block_bbox = block.get('bbox')
                if block_bbox and len(block_bbox) == 4:
                    width = float(block_bbox[2]) - float(block_bbox[0])
                    height = float(block_bbox[3]) - float(block_bbox[1])
                    image_area += width * height

        # Compute ratio
        if total_area == 0:
            return 0.0

        ratio = min(image_area / total_area, 1.0)
        return ratio

    def _compute_cta_keyword_score(self, text: str) -> float:
        """
        Compute score based on call-to-action keyword presence.

        Returns:
            Score between 0 and 1 (higher = more CTA keywords)
        """
        text_lower = text.lower()

        # Count matches for CTA keywords
        matches = 0
        for keyword in self.cta_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in text_lower:
                matches += 1
                # Multiple occurrences of same keyword count more
                count = text_lower.count(keyword_lower)
                if count > 1:
                    matches += (count - 1)

        # Normalize by word count to avoid rewarding very long text
        words = text.split()
        word_count = len(words)

        if word_count == 0:
            return 0.0

        # Score: matches per 100 words, capped at 1.0
        matches_per_100 = (matches / word_count) * 100
        score = min(matches_per_100 / 5.0, 1.0)  # 5+ CTA mentions per 100 words = max score

        return score

    def _compute_contact_density(self, text: str) -> float:
        """
        Compute score based on phone/email/contact information density.

        Returns:
            Score between 0 and 1 (higher = more contact info)
        """
        # Count phone numbers
        phone_matches = len(PHONE_RE.findall(text))

        # Count email addresses
        email_matches = len(EMAIL_RE.findall(text))

        # Count URLs/websites
        url_keywords = ['www.', 'http', '.com', '.ke', '.org', '.net']
        url_matches = sum(text.lower().count(kw) for kw in url_keywords)

        total_contacts = phone_matches + email_matches + url_matches

        # Normalize by word count
        words = text.split()
        word_count = len(words)

        if word_count == 0:
            return 0.0

        # Score: contacts per 100 words, capped at 1.0
        contacts_per_100 = (total_contacts / word_count) * 100
        score = min(contacts_per_100 / 10.0, 1.0)  # 10+ contacts per 100 words = max score

        return score

    def _compute_brand_token_score(self, text: str) -> float:
        """
        Compute score based on brand-like token patterns.

        Brand-like tokens: ALL CAPS, short (1-3 words), often repeated.

        Returns:
            Score between 0 and 1
        """
        # Split into tokens
        tokens = text.split()

        # Find brand-like tokens
        brand_like = []
        for token in tokens:
            # Check if all caps or title case
            clean_token = re.sub(r'[^\w\s]', '', token)  # Remove punctuation
            if len(clean_token) >= 3 and len(clean_token) <= 20:
                if clean_token.isupper() or (clean_token[0].isupper() and clean_token[1:].islower()):
                    brand_like.append(clean_token)

        if not brand_like:
            return 0.0

        # Check for repetition (brand names often repeated)
        token_counts = {}
        for token in brand_like:
            token_counts[token] = token_counts.get(token, 0) + 1

        # Count repeated tokens
        repeated = sum(1 for count in token_counts.values() if count > 1)

        # Score based on repetition and ratio
        ratio = len(brand_like) / len(tokens) if tokens else 0
        repetition_score = min(repeated / 3.0, 1.0)  # 3+ repeats = max score

        # Combine signals
        score = (ratio * 0.4) + (repetition_score * 0.6)

        return score

    def _compute_price_density(self, text: str) -> float:
        """
        Compute score based on price pattern density.

        Returns:
            Score between 0 and 1
        """
        # Count price pattern matches
        matches = 0
        for pattern in self.price_patterns:
            matches += text.lower().count(pattern.lower())

        # Normalize by word count
        words = text.split()
        word_count = len(words)

        if word_count == 0:
            return 0.0

        # Score: price mentions per 100 words, capped at 1.0
        prices_per_100 = (matches / word_count) * 100
        score = min(prices_per_100 / 8.0, 1.0)  # 8+ prices per 100 words = max score

        return score

    def _compute_length_penalty(self, text: str) -> float:
        """
        Compute penalty based on text length (longer text = less ad-like).

        Returns:
            Score between 0 and 1 (lower = longer = more story-like)
        """
        word_count = len(text.split())

        # Short text is more ad-like
        if word_count <= 30:
            return 1.0
        elif word_count <= 60:
            return 0.8
        elif word_count <= 120:
            return 0.5
        elif word_count <= 200:
            return 0.2
        else:
            return 0.0

    def _compute_layout_ad_boost(self, blocks_json: Optional[list[dict]]) -> float:
        """
        Compute boost if layout explicitly marks blocks as AD type.

        Returns:
            Score between 0 and 1
        """
        if not blocks_json:
            return 0.0

        # Count blocks with AD type
        ad_blocks = 0
        total_blocks = len(blocks_json)

        for block in blocks_json:
            block_type = (block.get('type', '') or '').lower()
            if 'ad' in block_type or 'advertisement' in block_type:
                ad_blocks += 1

        if total_blocks == 0:
            return 0.0

        # More ad blocks = higher score
        return ad_blocks / total_blocks

    def _combine_signals(self, signals: dict[str, float]) -> float:
        """
        Combine individual signals into final ad candidate score.

        Signal weights:
        - Image area: 20%
        - CTA keywords: 25%
        - Contact density: 20%
        - Brand tokens: 15%
        - Price density: 10%
        - Length penalty: 5%
        - Layout boost: 5%

        Returns:
            Combined score between 0 and 1
        """
        weights = {
            'image_area_ratio': 0.20,
            'cta_keyword_score': 0.25,
            'contact_density': 0.20,
            'brand_token_score': 0.15,
            'price_density': 0.10,
            'length_penalty': 0.05,
            'layout_ad_boost': 0.05,
        }

        total_score = 0.0
        for signal_name, weight in weights.items():
            signal_value = signals.get(signal_name, 0.0)
            total_score += signal_value * weight

        return max(0.0, min(1.0, total_score))

    def _generate_reasons(self, signals: dict[str, float], final_score: float) -> list[str]:
        """
        Generate human-readable reasons for ad classification.

        Returns:
            List of reason strings
        """
        reasons = []

        # High image area
        if signals.get('image_area_ratio', 0) > 0.3:
            reasons.append(f"High image area ratio ({signals['image_area_ratio']:.2f})")

        # CTA keywords
        if signals.get('cta_keyword_score', 0) > 0.4:
            reasons.append(f"Call-to-action keywords present (score: {signals['cta_keyword_score']:.2f})")

        # Contact information
        if signals.get('contact_density', 0) > 0.3:
            reasons.append(f"Contact information present (phone/email/URL)")

        # Brand-like tokens
        if signals.get('brand_token_score', 0) > 0.4:
            reasons.append(f"Brand-like token patterns detected")

        # Price information
        if signals.get('price_density', 0) > 0.3:
            reasons.append(f"Price patterns detected")

        # Short text
        if signals.get('length_penalty', 0) > 0.7:
            reasons.append(f"Short text length (ad-like)")

        # Layout AD type
        if signals.get('layout_ad_boost', 0) > 0:
            reasons.append(f"Layout type marked as AD")

        # If no specific reasons but score is high, add generic reason
        if not reasons and final_score > self.threshold:
            reasons.append("Multiple weak ad-like indicators")

        return reasons


def create_ad_detection_service() -> AdDetectionService:
    """Factory function to create AdDetectionService instance."""
    return AdDetectionService()
