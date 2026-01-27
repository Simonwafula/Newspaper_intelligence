from __future__ import annotations

from typing import Iterable, Tuple

from .schemas import BBox


def bbox_area(b: BBox) -> float:
    return max(0.0, b.x2 - b.x1) * max(0.0, b.y2 - b.y1)


def bbox_union(a: BBox, b: BBox) -> BBox:
    return BBox(
        x1=min(a.x1, b.x1),
        y1=min(a.y1, b.y1),
        x2=max(a.x2, b.x2),
        y2=max(a.y2, b.y2),
    )


def bbox_iou(a: BBox, b: BBox) -> float:
    inter_x1 = max(a.x1, b.x1)
    inter_y1 = max(a.y1, b.y1)
    inter_x2 = min(a.x2, b.x2)
    inter_y2 = min(a.y2, b.y2)

    inter = max(0.0, inter_x2 - inter_x1) * max(0.0, inter_y2 - inter_y1)
    if inter == 0.0:
        return 0.0
    union = bbox_area(a) + bbox_area(b) - inter
    return inter / union if union else 0.0


def x_overlap_ratio(a: BBox, b: BBox) -> float:
    inter_x1 = max(a.x1, b.x1)
    inter_x2 = min(a.x2, b.x2)
    inter = max(0.0, inter_x2 - inter_x1)
    if inter == 0.0:
        return 0.0
    width = min(a.x2 - a.x1, b.x2 - b.x1)
    return inter / width if width else 0.0


def bbox_from_blocks(blocks: Iterable[Tuple[float, float, float, float]]) -> BBox:
    xs1, ys1, xs2, ys2 = [], [], [], []
    for x1, y1, x2, y2 in blocks:
        xs1.append(x1)
        ys1.append(y1)
        xs2.append(x2)
        ys2.append(y2)
    return BBox(min(xs1), min(ys1), max(xs2), max(ys2))
