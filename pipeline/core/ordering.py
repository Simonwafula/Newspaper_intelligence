from __future__ import annotations

from dataclasses import replace
from typing import Dict, Iterable, List, Tuple

from .geom import bbox_union, x_overlap_ratio
from .schemas import Block, BBox


TOP_TYPES = {
    "headline": 0,
    "title": 0,
    "subhead": 1,
    "deck": 1,
    "byline": 2,
}

BODY_TYPES = {"body", "text", "paragraph"}


def estimate_line_height(block: Block) -> float:
    if block.words:
        heights = [w.bbox.y2 - w.bbox.y1 for w in block.words if w.bbox.y2 > w.bbox.y1]
        if heights:
            heights.sort()
            return heights[len(heights) // 2]
    height = max(1.0, block.bbox.y2 - block.bbox.y1)
    return max(10.0, min(40.0, height / 6.0))


def group_columns(blocks: Iterable[Block], x_overlap_threshold: float = 0.6) -> List[List[Block]]:
    columns: List[List[Block]] = []
    col_boxes: List[BBox] = []
    for block in sorted(blocks, key=lambda b: (b.bbox.x1, b.bbox.y1)):
        placed = False
        for idx, col_box in enumerate(col_boxes):
            if x_overlap_ratio(block.bbox, col_box) >= x_overlap_threshold:
                columns[idx].append(block)
                col_boxes[idx] = bbox_union(col_box, block.bbox)
                placed = True
                break
        if not placed:
            columns.append([block])
            col_boxes.append(block.bbox)
    return columns


def order_column(blocks: Iterable[Block]) -> List[Block]:
    blocks = list(blocks)
    top = [b for b in blocks if b.type in TOP_TYPES]
    rest = [b for b in blocks if b.type not in TOP_TYPES]
    top_sorted = sorted(top, key=lambda b: b.bbox.y1)
    rest_sorted = sorted(rest, key=lambda b: b.bbox.y1)
    return top_sorted + rest_sorted


def assign_columns(blocks: Iterable[Block], x_overlap_threshold: float = 0.6) -> List[Block]:
    columns = group_columns(blocks, x_overlap_threshold=x_overlap_threshold)
    out: List[Block] = []
    for idx, col in enumerate(columns):
        for b in col:
            out.append(replace(b, column=idx))
    return out


def merge_paragraphs(blocks: Iterable[Block], gap_multiplier: float = 1.5) -> List[Block]:
    blocks = list(blocks)
    if not blocks:
        return []
    merged: List[Block] = []
    i = 0
    while i < len(blocks):
        current = blocks[i]
        if current.type not in BODY_TYPES:
            merged.append(current)
            i += 1
            continue
        j = i + 1
        acc = current
        while j < len(blocks):
            nxt = blocks[j]
            if nxt.type not in BODY_TYPES:
                break
            if acc.column is not None and nxt.column is not None and acc.column != nxt.column:
                break
            gap = nxt.bbox.y1 - acc.bbox.y2
            line_height = estimate_line_height(acc)
            if gap > gap_multiplier * line_height:
                break
            if x_overlap_ratio(acc.bbox, nxt.bbox) < 0.7:
                break
            acc = _merge_blocks(acc, nxt)
            j += 1
        merged.append(acc)
        i = j
    return merged


def _merge_blocks(a: Block, b: Block) -> Block:
    joined_text = (a.text.strip() + " " + b.text.strip()).strip()
    words = a.words + b.words
    return Block(
        id=a.id,
        type=a.type,
        bbox=bbox_union(a.bbox, b.bbox),
        score=a.score,
        text=joined_text,
        words=words,
        page=a.page,
        column=a.column,
        meta={**a.meta, **b.meta},
    )


def order_blocks(blocks: Iterable[Block], x_overlap_threshold: float = 0.6) -> List[Block]:
    columns = group_columns(blocks, x_overlap_threshold=x_overlap_threshold)
    ordered: List[Block] = []
    for col_index, col in enumerate(columns):
        for b in col:
            b.column = col_index
        ordered.extend(order_column(col))
    ordered = merge_paragraphs(ordered)
    return ordered


def order_pages(pages: Iterable[Tuple[int, List[Block]]]) -> Dict[int, List[Block]]:
    ordered: Dict[int, List[Block]] = {}
    for page_num, blocks in pages:
        ordered[page_num] = order_blocks(blocks)
    return ordered
