"""
Reading Order Service - Phase 2 Implementation

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
from typing import Any, List

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
            print(f"Block {block['id']} has reading order {block['reading_order']}")
    """

    def __init__(self, x_overlap_threshold: float = 0.6):
        """
        Initialize the reading order service.

        Args:
            x_overlap_threshold: Minimum x-axis overlap ratio to consider blocks in same column
        """
        self.x_overlap_threshold = x_overlap_threshold
        logger.info("Initializing ReadingOrderService")

    def assign_reading_order(self, blocks: List[dict], page_width: float) -> List[dict]:
        """
        Assign reading order to blocks based on column layout.

        Args:
            blocks: List of block dictionaries with 'bbox' key
            page_width: Page width for column detection

        Returns:
            Same blocks list with 'reading_order' and 'column_index' fields added
        """
        if not blocks:
            return blocks

        # Detect columns and assign column indices
        columns = self._detect_columns(blocks)

        # Assign reading order
        reading_order = 1
        for col_idx, (_, col_blocks) in enumerate(columns):
            # Sort blocks within column by y-position (top to bottom)
            sorted_blocks = sorted(col_blocks, key=lambda b: b['bbox'][1])

            for block in sorted_blocks:
                block['reading_order'] = reading_order
                block['column_index'] = col_idx
                reading_order += 1

        logger.info(
            f"Assigned reading order to {len(blocks)} blocks across {len(columns)} columns"
        )
        return blocks

    def _detect_columns(self, blocks: List[dict]) -> List[tuple[float, List[dict]]]:
        """
        Detect column layout and group blocks by column.

        Reuses logic from layout_analyzer.py _assign_columns().

        Args:
            blocks: List of all blocks

        Returns:
            List of (x_position, column_blocks) tuples, sorted left to right
        """
        if not blocks:
            return []

        columns: List[List[dict]] = []
        col_boxes: List[List[float]] = []

        # Sort blocks by x-position first, then y-position
        sorted_blocks = sorted(
            blocks, key=lambda b: (b['bbox'][0], b['bbox'][1])
        )

        for block in sorted_blocks:
            bbox = block['bbox']
            placed = False

            # Try to place block in existing column
            for idx, col_box in enumerate(col_boxes):
                if self._x_overlap_ratio(bbox, col_box) >= self.x_overlap_threshold:
                    columns[idx].append(block)
                    # Expand column bounding box
                    col_boxes[idx] = self._bbox_union(col_box, bbox)
                    placed = True
                    break

            # Create new column if block doesn't fit in existing ones
            if not placed:
                columns.append([block])
                col_boxes.append(bbox[:])  # Copy bbox

        # Sort columns by x-position (left to right)
        ordered_columns = sorted(
            [(col_boxes[i][0], columns[i]) for i in range(len(columns))],
            key=lambda item: item[0],
        )

        logger.debug(f"Detected {len(ordered_columns)} columns")
        return ordered_columns

    def _x_overlap_ratio(self, bbox1: List[float], bbox2: List[float]) -> float:
        """
        Calculate horizontal overlap ratio between two bboxes.

        Args:
            bbox1: [x0, y0, x1, y1]
            bbox2: [x0, y0, x1, y1]

        Returns:
            Overlap ratio (0-1)
        """
        x1_min, _, x1_max, _ = bbox1
        x2_min, _, x2_max, _ = bbox2

        # Calculate overlap
        overlap_start = max(x1_min, x2_min)
        overlap_end = min(x1_max, x2_max)
        overlap = max(0, overlap_end - overlap_start)

        # Calculate minimum width
        width1 = x1_max - x1_min
        width2 = x2_max - x2_min
        min_width = min(width1, width2)

        if min_width == 0:
            return 0.0

        return overlap / min_width

    def _bbox_union(self, bbox1: List[float], bbox2: List[float]) -> List[float]:
        """
        Calculate the union of two bounding boxes.

        Args:
            bbox1: [x0, y0, x1, y1]
            bbox2: [x0, y0, x1, y1]

        Returns:
            Union bbox [x0, y0, x1, y1]
        """
        return [
            min(bbox1[0], bbox2[0]),  # x0
            min(bbox1[1], bbox2[1]),  # y0
            max(bbox1[2], bbox2[2]),  # x1
            max(bbox1[3], bbox2[3]),  # y1
        ]
