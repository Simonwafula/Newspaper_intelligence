from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def to_list(self) -> List[float]:
        return [self.x1, self.y1, self.x2, self.y2]

    @classmethod
    def from_list(cls, v: List[float]) -> "BBox":
        return cls(float(v[0]), float(v[1]), float(v[2]), float(v[3]))


@dataclass
class Word:
    text: str
    bbox: BBox
    conf: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "bbox": self.bbox.to_list(),
            "conf": self.conf,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Word":
        return cls(
            text=str(data.get("text", "")),
            bbox=BBox.from_list(data["bbox"]),
            conf=data.get("conf"),
        )


@dataclass
class Block:
    id: str
    type: str
    bbox: BBox
    score: Optional[float] = None
    text: str = ""
    words: List[Word] = field(default_factory=list)
    page: Optional[int] = None
    column: Optional[int] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "bbox": self.bbox.to_list(),
            "score": self.score,
            "text": self.text,
            "words": [w.to_dict() for w in self.words],
            "page": self.page,
            "column": self.column,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Block":
        return cls(
            id=str(data.get("id", "")),
            type=str(data.get("type", "")),
            bbox=BBox.from_list(data["bbox"]),
            score=data.get("score"),
            text=str(data.get("text", "")),
            words=[Word.from_dict(w) for w in data.get("words", [])],
            page=data.get("page"),
            column=data.get("column"),
            meta=dict(data.get("meta", {})),
        )


@dataclass
class Page:
    number: int
    width: int
    height: int
    image_path: Optional[str] = None
    blocks: List[Block] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "width": self.width,
            "height": self.height,
            "image_path": self.image_path,
            "blocks": [b.to_dict() for b in self.blocks],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Page":
        return cls(
            number=int(data["number"]),
            width=int(data["width"]),
            height=int(data["height"]),
            image_path=data.get("image_path"),
            blocks=[Block.from_dict(b) for b in data.get("blocks", [])],
        )


@dataclass
class Story:
    id: str
    headline: str
    section: Optional[str]
    byline: Optional[str]
    text: str
    pages: List[int]
    block_ids: List[str]
    blocks: List[Block] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "headline": self.headline,
            "section": self.section,
            "byline": self.byline,
            "text": self.text,
            "pages": self.pages,
            "block_ids": self.block_ids,
            "blocks": [b.to_dict() for b in self.blocks],
            "meta": self.meta,
        }
