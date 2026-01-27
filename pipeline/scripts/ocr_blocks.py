from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List, Optional

from PIL import Image

from pipeline.core.io import load_pages
from pipeline.core.schemas import BBox, Word


TEXT_TYPES = {"headline", "title", "subhead", "deck", "byline", "body", "text", "caption", "section"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", required=True, help="Path to pages.json")
    parser.add_argument("--out", required=True, help="Output pages.json")
    parser.add_argument("--engine", default="paddle", choices=["paddle", "tesseract"])
    parser.add_argument("--lang", default="en")
    parser.add_argument("--min-conf", type=float, default=0.5)
    parser.add_argument("--types", default="", help="Comma-separated block types to OCR")
    args = parser.parse_args()

    if args.engine == "paddle":
        ocr = build_paddle_ocr(args.lang)
    else:
        ocr = build_tesseract_ocr(args.lang)

    types = set(t.strip() for t in args.types.split(",") if t.strip())
    if not types:
        types = TEXT_TYPES

    pages = load_pages(args.pages)
    for page in pages:
        if not page.image_path:
            continue
        img = Image.open(page.image_path).convert("RGB")
        for block in page.blocks:
            if block.type not in types:
                continue
            words, text = ocr_block(img, block.bbox, ocr, args.engine, args.min_conf)
            block.words = words
            block.text = text

    Path(args.out).write_text(json.dumps([p.to_dict() for p in pages], indent=2))
    print(f"Wrote OCR -> {args.out}")


def build_paddle_ocr(lang: str):
    try:
        from paddleocr import PaddleOCR
    except Exception as exc:
        raise SystemExit(
            "PaddleOCR is not installed. Install with: pip install paddleocr"
        ) from exc
    return PaddleOCR(use_angle_cls=True, lang=lang)


def build_tesseract_ocr(lang: str):
    try:
        import pytesseract
    except Exception as exc:
        raise SystemExit(
            "pytesseract is not installed. Install with: pip install pytesseract"
        ) from exc
    return pytesseract


def ocr_block(img: Image.Image, bbox: BBox, ocr, engine: str, min_conf: float):
    x1, y1, x2, y2 = clamp_bbox(bbox, img.width, img.height)
    crop = img.crop((x1, y1, x2, y2))
    if engine == "paddle":
        return paddle_ocr(crop, x1, y1, ocr, min_conf)
    return tesseract_ocr(crop, x1, y1, ocr, min_conf)


def paddle_ocr(crop: Image.Image, offset_x: float, offset_y: float, ocr, min_conf: float):
    try:
        import numpy as np
    except Exception as exc:
        raise SystemExit("NumPy is required for PaddleOCR.") from exc
    results = ocr.ocr(np.array(crop), cls=True)
    words: List[Word] = []
    texts: List[str] = []
    if results and results[0]:
        for line in results[0]:
            box, (text, conf) = line
            if conf is not None and conf < min_conf:
                continue
            xs = [pt[0] for pt in box]
            ys = [pt[1] for pt in box]
            word_bbox = BBox(
                x1=offset_x + float(min(xs)),
                y1=offset_y + float(min(ys)),
                x2=offset_x + float(max(xs)),
                y2=offset_y + float(max(ys)),
            )
            words.append(Word(text=text, bbox=word_bbox, conf=float(conf) if conf is not None else None))
            texts.append(text)
    return words, " ".join(texts).strip()


def tesseract_ocr(crop: Image.Image, offset_x: float, offset_y: float, ocr, min_conf: float):
    data = ocr.image_to_data(crop, output_type=ocr.Output.DICT)
    words: List[Word] = []
    texts: List[str] = []
    n = len(data.get("text", []))
    for i in range(n):
        text = data["text"][i].strip()
        if not text:
            continue
        conf = float(data["conf"][i]) if data["conf"][i] != "-1" else None
        if conf is not None and conf < min_conf * 100:
            continue
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        word_bbox = BBox(
            x1=offset_x + x,
            y1=offset_y + y,
            x2=offset_x + x + w,
            y2=offset_y + y + h,
        )
        words.append(Word(text=text, bbox=word_bbox, conf=conf))
        texts.append(text)
    return words, " ".join(texts).strip()


def clamp_bbox(bbox: BBox, width: int, height: int):
    x1 = max(0, min(width, int(bbox.x1)))
    y1 = max(0, min(height, int(bbox.y1)))
    x2 = max(0, min(width, int(bbox.x2)))
    y2 = max(0, min(height, int(bbox.y2)))
    if x2 <= x1:
        x2 = min(width, x1 + 1)
    if y2 <= y1:
        y2 = min(height, y1 + 1)
    return x1, y1, x2, y2


if __name__ == "__main__":
    main()
