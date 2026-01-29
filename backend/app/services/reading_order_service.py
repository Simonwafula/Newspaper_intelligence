"""
Reading Order Service - Phase 2/5 Implementation

This service assigns reading order to detected layout blocks, handling
multi-column newspaper layouts correctly.

Key challenges in newspaper reading order:
- Multi-column layouts (2-6 columns)
- Column jumps and wrapping
- Headlines spanning multiple columns
- Mixed column widths
- Section headers and ads breaking flow
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class ReadingOrderService:
    """
    Service for assigning reading order to layout blocks.

    Handles multi-column newspaper layouts by:
    1. Detecting column boundaries
    2. Grouping blocks by column
    3. Sorting blocks within each column by vertical position
    4. Assigning sequential reading_order numbers

    Usage:
        service = ReadingOrderService()
        ordered_blocks = service.assign_reading_order(blocks, page_width)
        for block in ordered_blocks:
            print(f"Block {block.id} has reading order {block.reading_order}")
    """

    def __init__(self):
        """Initialize the reading order service."""
        logger.info("Initializing ReadingOrderService")

    def assign_reading_order(
        self, blocks: List["DetectedBlock"], page_width: float
    ) -> List["DetectedBlock"]:
        """
        Assign reading order to blocks based on column layout.

        Args:
            blocks: List of DetectedBlock objects with bboxes
            page_width: Page width for column detection

        Returns:
            Same blocks list with reading_order field populated

        Implementation Notes (Phase 2 or Phase 5):
            1. Detect columns:
               - Use _detect_columns() from layout_analyzer.py
               - Group blocks by x-coordinate overlap
               - Handle variable column widths

            2. Sort within columns:
               - Primary key: column_index (left to right)
               - Secondary key: y-position (top to bottom)
               - Handle headlines that span columns

            3. Assign order:
               - Sequential numbers: 1, 2, 3, ...
               - Add reading_order attribute to each block
               - Also add column_index for reference

            4. Special cases:
               - Section headers: Usually span all columns, get low order
               - Images/captions: Order based on their position
               - Ads: Include in flow or mark separately

        Reuse existing logic from:
            backend/app/services/layout_analyzer.py:
            - _assign_columns() (lines 337-361)
            - _sort_blocks_by_reading_order() (lines 326-335)
        """
        raise NotImplementedError(
            "Phase 2 or Phase 5: Implement reading order assignment. "
            "Reuse column detection logic from layout_analyzer.py. "
            "See plan file for detailed implementation guidance."
        )

    def _detect_columns(
        self, blocks: List["DetectedBlock"], page_width: float
    ) -> List[List["DetectedBlock"]]:
        """
        Detect column layout and group blocks by column.

        Args:
            blocks: List of all blocks
            page_width: Page width

        Returns:
            List of column groups, each containing blocks in that column

        Implementation Notes (Phase 2/5):
            1. Calculate x-centers for all blocks
            2. Use clustering (e.g., k-means or gap-based)
            3. Common newspaper layouts:
               - 2 columns: split at ~50%
               - 3 columns: split at ~33%, ~67%
               - 4+ columns: detect gaps in x-distribution

            Reference: layout_analyzer.py _assign_columns()
        """
        raise NotImplementedError("Phase 2/5: Implement column detection")

    def _sort_within_column(self, column_blocks: List["DetectedBlock"]) -> List["DetectedBlock"]:
        """
        Sort blocks within a column by vertical position.

        Args:
            column_blocks: Blocks in a single column

        Returns:
            Sorted blocks (top to bottom)

        Implementation:
            - Sort by y0 (top of bbox)
            - Handle overlapping blocks (headlines over body)
            - Headlines with large font should come before overlapping body text
        """
        return sorted(column_blocks, key=lambda b: b.bbox[1])  # Sort by y0

    def _handle_spanning_elements(
        self, blocks: List["DetectedBlock"], columns: List[List["DetectedBlock"]]
    ) -> List["DetectedBlock"]:
        """
        Handle elements that span multiple columns (headlines, section labels).

        Args:
            blocks: All blocks
            columns: Detected columns

        Returns:
            Blocks with adjusted reading order for spanning elements

        Implementation Notes:
            - Detect blocks wider than a single column
            - Place them before blocks in the columns they span
            - Typically: section labels first, then headlines, then body
        """
        raise NotImplementedError("Phase 2/5: Implement spanning element handling")
