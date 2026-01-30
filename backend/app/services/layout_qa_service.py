"""
Layout QA Service - Computes layout quality metrics and implements smart fallback.

This service provides:
- Page-level layout quality assessment
- Automatic fallback to heuristic processing when needed
- Detailed logging of QA metrics and fallback reasons
"""

import logging
from typing import Any, Optional

from app.settings import settings

logger = logging.getLogger(__name__)


class LayoutQAService:
    """Service for layout quality assessment and fallback logic."""

    def __init__(self):
        self.qa_enabled = settings.layout_qa_enabled
        self.fallback_enabled = settings.layout_fallback_enabled
        self.confidence_min = settings.layout_confidence_min
        self.coverage_min = settings.layout_coverage_min

    def compute_layout_qa_metrics(
        self,
        page_info: dict[str, Any],
        layout_confidence: Optional[float] = None,
        layout_method: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Compute layout quality assurance metrics for a page.

        Args:
            page_info: Dictionary containing page information and blocks
            layout_confidence: Confidence score from ML layout detection (if available)
            layout_method: Method used for layout detection ('ml', 'heuristic', etc.)

        Returns:
            Dictionary of QA metrics including coverage, block counts, quality score
        """
        text_blocks = page_info.get('text_blocks', [])
        blocks_json = page_info.get('blocks_json', [])
        bbox_json = page_info.get('bbox_json')
        page_width = float(page_info.get('width', 0))
        page_height = float(page_info.get('height', 0))

        # Initialize metrics
        metrics = {
            'layout_coverage_ratio': 0.0,
            'num_blocks_total': 0,
            'num_blocks_body': 0,
            'num_blocks_headline': 0,
            'num_blocks_image': 0,
            'num_blocks_caption': 0,
            'num_blocks_ad': 0,
            'column_count_estimate': 1,
            'headline_candidates_count': 0,
            'layout_quality_score': 0.0,
        }

        # Use blocks_json if available, otherwise fall back to text_blocks
        blocks = blocks_json if blocks_json else text_blocks

        if not blocks:
            logger.warning(f"Page has no blocks, QA metrics will be zero")
            return metrics

        metrics['num_blocks_total'] = len(blocks)

        # Count blocks by type
        for block in blocks:
            block_type = block.get('type', 'text').lower()
            if 'body' in block_type or 'text' in block_type:
                metrics['num_blocks_body'] += 1
            elif 'headline' in block_type or 'title' in block_type or 'heading' in block_type:
                metrics['num_blocks_headline'] += 1
            elif 'image' in block_type or 'figure' in block_type:
                metrics['num_blocks_image'] += 1
            elif 'caption' in block_type:
                metrics['num_blocks_caption'] += 1
            elif 'ad' in block_type or 'advertisement' in block_type:
                metrics['num_blocks_ad'] += 1

        # Count headline candidates (blocks that look like headlines)
        metrics['headline_candidates_count'] = self._count_headline_candidates(blocks)

        # Estimate column count from x-positions
        metrics['column_count_estimate'] = self._estimate_column_count(blocks, page_width)

        # Compute page coverage ratio (fraction of page area covered by blocks)
        metrics['layout_coverage_ratio'] = self._compute_coverage_ratio(blocks, page_width, page_height)

        # Compute overall quality score
        metrics['layout_quality_score'] = self._compute_quality_score(
            metrics,
            layout_confidence=layout_confidence,
            layout_method=layout_method
        )

        return metrics

    def should_use_fallback(
        self,
        qa_metrics: dict[str, Any],
        layout_confidence: Optional[float] = None,
        layout_method: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if fallback to heuristic processing should be used.

        Args:
            qa_metrics: Dictionary of QA metrics from compute_layout_qa_metrics
            layout_confidence: Confidence score from ML layout detection
            layout_method: Method used for layout detection

        Returns:
            Tuple of (should_fallback, reason_string)
        """
        if not self.fallback_enabled:
            return False, None

        # Check 1: Layout confidence too low
        if layout_confidence is not None and layout_confidence < self.confidence_min:
            return True, f"Low layout confidence ({layout_confidence:.3f} < {self.confidence_min})"

        # Check 2: Coverage too low (not enough of page analyzed)
        coverage = qa_metrics.get('layout_coverage_ratio', 0)
        if coverage < self.coverage_min:
            return True, f"Low page coverage ({coverage:.3f} < {self.coverage_min})"

        # Check 3: Suspicious block distribution
        # Very few blocks for a typical page
        if qa_metrics.get('num_blocks_total', 0) < 3:
            return True, f"Suspiciously few blocks ({qa_metrics['num_blocks_total']})"

        # Too many ad blocks compared to content
        total_blocks = qa_metrics.get('num_blocks_total', 1)
        ad_blocks = qa_metrics.get('num_blocks_ad', 0)
        body_blocks = qa_metrics.get('num_blocks_body', 0)
        if ad_blocks > body_blocks and body_blocks > 0:
            ad_ratio = ad_blocks / body_blocks
            if ad_ratio > 2.0:  # More than 2x ads than content
                return True, f"Unusual ad/content ratio ({ad_ratio:.2f})"

        # Check 4: No headline candidates
        if qa_metrics.get('headline_candidates_count', 0) == 0:
            # Might be okay for classifieds pages, but suspicious for news
            return True, "No headline candidates detected"

        # Check 5: Very low quality score
        quality = qa_metrics.get('layout_quality_score', 0)
        if quality < 0.3:
            return True, f"Low overall quality score ({quality:.3f})"

        return False, None

    def _count_headline_candidates(self, blocks: list[dict]) -> int:
        """Count blocks that look like headlines."""
        count = 0

        for block in blocks:
            text = block.get('text', '').strip()
            if not text or len(text) < 5 or len(text) > 200:
                continue

            # Check headline-like characteristics
            is_short = len(text) < 100
            is_title_case = self._is_title_case(text)
            is_all_caps = text.isupper()
            has_large_font = self._has_large_font(block)

            # Consider it a headline candidate if it has multiple indicators
            score = 0
            if is_short:
                score += 1
            if is_title_case:
                score += 2
            if is_all_caps:
                score += 2
            if has_large_font:
                score += 3

            if score >= 3:
                count += 1

        return count

    def _is_title_case(self, text: str) -> bool:
        """Check if text is in title case."""
        words = text.split()
        if not words:
            return False

        # Count words starting with uppercase
        title_case_words = sum(1 for word in words if word and word[0].isupper())
        ratio = title_case_words / len(words)

        return ratio > 0.6

    def _has_large_font(self, block: dict) -> bool:
        """Check if block has larger-than-typical font."""
        font_size = block.get('font_size')
        if isinstance(font_size, (int, float)) and font_size > 0:
            return font_size > 14

        # Estimate from bbox if no font_size
        bbox = block.get('bbox')
        if bbox and len(bbox) == 4:
            height = float(bbox[3]) - float(bbox[1])
            text = block.get('text', '')
            line_count = max(1, text.count('\n') + 1)
            estimated_font = height / line_count if line_count else 0
            return estimated_font > 14

        return False

    def _estimate_column_count(self, blocks: list[dict], page_width: float) -> int:
        """Estimate the number of columns from block x-positions."""
        if page_width <= 0 or not blocks:
            return 1

        # Get unique x-positions
        x_positions = set()
        for block in blocks:
            bbox = block.get('bbox')
            if bbox and len(bbox) >= 2:
                x_positions.add(float(bbox[0]))  # left edge

        if not x_positions:
            return 1

        sorted_x = sorted(x_positions)

        # Count significant gaps (column boundaries)
        # A gap is significant if it's > 8% of page width
        significant_gaps = 0
        for i in range(1, len(sorted_x)):
            gap = sorted_x[i] - sorted_x[i-1]
            if gap > page_width * 0.08:
                significant_gaps += 1

        # Number of columns = gaps + 1, capped at 6
        return min(6, significant_gaps + 1)

    def _compute_coverage_ratio(
        self,
        blocks: list[dict],
        page_width: float,
        page_height: float
    ) -> float:
        """
        Compute the fraction of page area covered by detected blocks.

        Args:
            blocks: List of blocks with bbox coordinates
            page_width: Page width in pixels
            page_height: Page height in pixels

        Returns:
            Coverage ratio between 0 and 1
        """
        if page_width <= 0 or page_height <= 0 or not blocks:
            return 0.0

        page_area = page_width * page_height
        if page_area == 0:
            return 0.0

        # Sum block areas (with deduplication for overlapping blocks)
        # For simplicity, we'll just sum areas and clamp at page_area
        total_block_area = 0.0

        for block in blocks:
            bbox = block.get('bbox')
            if bbox and len(bbox) == 4:
                width = float(bbox[2]) - float(bbox[0])
                height = float(bbox[3]) - float(bbox[1])
                block_area = width * height
                total_block_area += block_area

        # Clamp to page area (handles overlapping blocks)
        coverage = min(total_block_area / page_area, 1.0)
        return coverage

    def _compute_quality_score(
        self,
        metrics: dict[str, Any],
        layout_confidence: Optional[float] = None,
        layout_method: Optional[str] = None
    ) -> float:
        """
        Compute overall layout quality score (0-1).

        Combines multiple signals:
        - Layout confidence (if available)
        - Coverage ratio
        - Block count sanity
        - Column distribution
        - Headline presence

        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.0
        weights = []

        # Signal 1: Layout confidence (if ML-based)
        if layout_confidence is not None and layout_method == 'ml':
            # Weight layout confidence heavily
            weights.append(0.3)
            score += layout_confidence * 0.3

        # Signal 2: Coverage ratio
        coverage = metrics.get('layout_coverage_ratio', 0)
        # Ideal coverage is 0.3-0.7 (not too sparse, not over-segmented)
        if 0.3 <= coverage <= 0.7:
            coverage_score = 1.0
        elif coverage < 0.3:
            coverage_score = coverage / 0.3  # Linear penalty
        else:  # coverage > 0.7
            coverage_score = max(0.0, 1.0 - (coverage - 0.7) / 0.3)
        weights.append(0.25)
        score += coverage_score * 0.25

        # Signal 3: Block count sanity
        num_blocks = metrics.get('num_blocks_total', 0)
        if 5 <= num_blocks <= 30:
            block_score = 1.0
        elif num_blocks < 5:
            block_score = num_blocks / 5.0
        else:  # num_blocks > 30
            block_score = max(0.0, 1.0 - (num_blocks - 30) / 20.0)
        weights.append(0.15)
        score += block_score * 0.15

        # Signal 4: Column count
        columns = metrics.get('column_count_estimate', 1)
        # Most newspapers have 2-4 columns
        if 2 <= columns <= 4:
            column_score = 1.0
        elif columns == 1:
            column_score = 0.7
        else:  # columns > 4
            column_score = max(0.0, 1.0 - (columns - 4) / 2.0)
        weights.append(0.15)
        score += column_score * 0.15

        # Signal 5: Headline presence
        headlines = metrics.get('headline_candidates_count', 0)
        # Ideal is 1-5 headlines per page
        if 1 <= headlines <= 5:
            headline_score = 1.0
        elif headlines == 0:
            headline_score = 0.3  # Might be okay for some pages
        else:  # headlines > 5
            headline_score = max(0.0, 1.0 - (headlines - 5) / 5.0)
        weights.append(0.15)
        score += headline_score * 0.15

        # Normalize score by total weights
        total_weight = sum(weights)
        if total_weight > 0:
            score = score / total_weight

        return max(0.0, min(1.0, score))


def create_layout_qa_service() -> LayoutQAService:
    """Factory function to create LayoutQAService instance."""
    return LayoutQAService()
