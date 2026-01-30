"""
Layout Assembler Service - Phase 5 Implementation

This service groups detected layout blocks into logical Items (stories, ads, classifieds).
It bridges ML-based layout detection with the existing Item model.

Grouping logic:
- HEADLINE/SUBHEADLINE + nearby BODY blocks → STORY
- AD blocks → standalone AD items
- IMAGE + CAPTION → IMAGE item (future)
- Maintains reading order and spatial relationships
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from app.services.layout_detection_service import DetectedBlock

logger = logging.getLogger(__name__)


class ItemGroup:
    """Represents a group of blocks that form a single Item."""

    def __init__(self, item_type: str, item_subtype: Optional[str] = None):
        self.item_type = item_type  # STORY, AD, CLASSIFIED, IMAGE
        self.item_subtype = item_subtype  # For future classification
        self.blocks: List[DetectedBlock] = []

    def add_block(self, block: "DetectedBlock"):
        """Add a block to this item group."""
        self.blocks.append(block)

    def get_bbox(self) -> List[float]:
        """Calculate bounding box encompassing all blocks."""
        if not self.blocks:
            return [0.0, 0.0, 0.0, 0.0]

        x0 = min(b.bbox[0] for b in self.blocks)
        y0 = min(b.bbox[1] for b in self.blocks)
        x1 = max(b.bbox[2] for b in self.blocks)
        y1 = max(b.bbox[3] for b in self.blocks)
        return [x0, y0, x1, y1]

    def get_text(self) -> str:
        """Get concatenated text from all blocks in reading order."""
        sorted_blocks = sorted(self.blocks, key=lambda b: b.id)
        return "\n\n".join(b.text for b in sorted_blocks if b.text)

    def to_dict(self) -> dict:
        """Convert to dictionary for Item.blocks_json."""
        return {
            "item_type": self.item_type,
            "item_subtype": self.item_subtype,
            "bbox": self.get_bbox(),
            "text": self.get_text(),
            "blocks": [
                {
                    "id": block.id,
                    "type": block.type,
                    "text": block.text,
                    "bbox": block.bbox,
                    "confidence": block.confidence,
                    "words": block.words,
                }
                for block in sorted(self.blocks, key=lambda b: b.id)
            ],
        }


class LayoutAssembler:
    """
    Service for assembling detected blocks into Items.

    Groups layout blocks based on:
    - Block type (HEADLINE, BODY, AD, etc.)
    - Spatial proximity
    - Reading order
    - Semantic relationships

    Usage:
        assembler = LayoutAssembler()
        item_groups = assembler.assemble_items(detected_blocks)
        for group in item_groups:
            # Create Item with group.to_dict()
    """

    def __init__(
        self,
        proximity_threshold: float = 0.05,  # 5% of page height
        headline_body_max_distance: float = 0.1,  # 10% of page height
    ):
        """
        Initialize the layout assembler.

        Args:
            proximity_threshold: Max distance between blocks to consider them related
            headline_body_max_distance: Max vertical distance from headline to body
        """
        self.proximity_threshold = proximity_threshold
        self.headline_body_max_distance = headline_body_max_distance
        logger.info("Initializing LayoutAssembler")

    def assemble_items(self, blocks: List["DetectedBlock"]) -> List[ItemGroup]:
        """
        Assemble detected blocks into logical Items.

        Args:
            blocks: List of DetectedBlock from layout detection + OCR

        Returns:
            List of ItemGroup objects representing stories, ads, etc.
        """
        if not blocks:
            return []

        # Sort blocks by reading order (should already be assigned)
        sorted_blocks = sorted(blocks, key=lambda b: b.id)

        item_groups: List[ItemGroup] = []
        used_blocks = set()

        # Strategy 1: Group headlines with nearby body text
        for block in sorted_blocks:
            if block.id in used_blocks:
                continue

            if block.type in ["HEADLINE", "SUBHEADLINE"]:
                story_group = self._create_story_group(block, sorted_blocks, used_blocks)
                if story_group:
                    item_groups.append(story_group)
                    for b in story_group.blocks:
                        used_blocks.add(b.id)

        # Strategy 2: Standalone ads
        for block in sorted_blocks:
            if block.id in used_blocks:
                continue

            if block.type == "AD":
                ad_group = ItemGroup(item_type="AD")
                ad_group.add_block(block)
                item_groups.append(ad_group)
                used_blocks.add(block.id)

        # Strategy 3: Orphaned body text (no headline) → standalone stories
        for block in sorted_blocks:
            if block.id in used_blocks:
                continue

            if block.type in ["BODY", "TEXT"]:
                # Create standalone story from orphaned body text
                story_group = ItemGroup(item_type="STORY")
                story_group.add_block(block)

                # Try to find continuation blocks nearby
                continuation = self._find_continuation_blocks(
                    block, sorted_blocks, used_blocks
                )
                for cont_block in continuation:
                    story_group.add_block(cont_block)
                    used_blocks.add(cont_block.id)

                item_groups.append(story_group)
                used_blocks.add(block.id)

        # Strategy 4: Everything else (section labels, images, etc.)
        for block in sorted_blocks:
            if block.id in used_blocks:
                continue

            # Create generic item for remaining blocks
            item_type = self._map_block_type_to_item_type(block.type)
            generic_group = ItemGroup(item_type=item_type)
            generic_group.add_block(block)
            item_groups.append(generic_group)
            used_blocks.add(block.id)

        logger.info(
            f"Assembled {len(item_groups)} items from {len(blocks)} blocks "
            f"({len(used_blocks)} blocks used)"
        )

        return item_groups

    def _create_story_group(
        self,
        headline_block: "DetectedBlock",
        all_blocks: List["DetectedBlock"],
        used_blocks: set,
    ) -> Optional[ItemGroup]:
        """
        Create a story group starting from a headline block.

        Args:
            headline_block: Starting HEADLINE or SUBHEADLINE block
            all_blocks: All available blocks
            used_blocks: Set of already-used block IDs

        Returns:
            ItemGroup with headline + body blocks, or None if no body found
        """
        story_group = ItemGroup(item_type="STORY")
        story_group.add_block(headline_block)

        # Find body blocks near this headline
        headline_bbox = headline_block.bbox
        headline_y_bottom = headline_bbox[3]

        # Look for body blocks below the headline
        for block in all_blocks:
            if block.id in used_blocks or block.id == headline_block.id:
                continue

            if block.type not in ["BODY", "TEXT"]:
                continue

            # Check vertical proximity (block should be below headline)
            block_y_top = block.bbox[1]
            vertical_distance = block_y_top - headline_y_bottom

            if 0 <= vertical_distance <= self.headline_body_max_distance:
                # Check horizontal overlap (same column)
                if self._has_horizontal_overlap(headline_bbox, block.bbox):
                    story_group.add_block(block)

        # Only return story if we found body text
        if len(story_group.blocks) > 1:
            return story_group

        # No body found, treat headline as standalone story
        return story_group

    def _find_continuation_blocks(
        self,
        start_block: "DetectedBlock",
        all_blocks: List["DetectedBlock"],
        used_blocks: set,
    ) -> List["DetectedBlock"]:
        """
        Find continuation blocks near the start block.

        Args:
            start_block: Starting block
            all_blocks: All available blocks
            used_blocks: Set of already-used block IDs

        Returns:
            List of continuation blocks
        """
        continuation = []
        current_bbox = start_block.bbox

        for block in all_blocks:
            if block.id in used_blocks or block.id == start_block.id:
                continue

            if block.type not in ["BODY", "TEXT"]:
                continue

            # Check if block is near current position
            block_y_top = block.bbox[1]
            current_y_bottom = current_bbox[3]
            vertical_distance = block_y_top - current_y_bottom

            if 0 <= vertical_distance <= self.proximity_threshold:
                if self._has_horizontal_overlap(current_bbox, block.bbox):
                    continuation.append(block)
                    current_bbox = block.bbox  # Update for next iteration

        return continuation

    def _has_horizontal_overlap(self, bbox1: List[float], bbox2: List[float]) -> bool:
        """
        Check if two bboxes have horizontal overlap (same column).

        Args:
            bbox1: [x0, y0, x1, y1]
            bbox2: [x0, y0, x1, y1]

        Returns:
            True if bboxes overlap horizontally
        """
        x1_start, _, x1_end, _ = bbox1
        x2_start, _, x2_end, _ = bbox2

        overlap_start = max(x1_start, x2_start)
        overlap_end = min(x1_end, x2_end)
        overlap = max(0, overlap_end - overlap_start)

        # Calculate minimum width
        width1 = x1_end - x1_start
        width2 = x2_end - x2_start
        min_width = min(width1, width2)

        if min_width == 0:
            return False

        overlap_ratio = overlap / min_width
        return overlap_ratio >= 0.5  # 50% overlap threshold

    def _map_block_type_to_item_type(self, block_type: str) -> str:
        """
        Map block type to Item type.

        Args:
            block_type: Block type from layout detection

        Returns:
            Item type (STORY, AD, CLASSIFIED, IMAGE)
        """
        type_map = {
            "HEADLINE": "STORY",
            "SUBHEADLINE": "STORY",
            "BODY": "STORY",
            "TEXT": "STORY",
            "AD": "AD",
            "IMAGE": "IMAGE",
            "CAPTION": "IMAGE",
            "TABLE": "STORY",
            "SECTION_LABEL": "STORY",
        }
        return type_map.get(block_type, "STORY")
