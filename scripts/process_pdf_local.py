#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "backend"))

from app.services.layout_analyzer import create_layout_analyzer
from app.services.ocr_service import create_ocr_service
from app.services.pdf_processor import create_pdf_processor
from app.services.story_grouping import build_story_groups
from app.settings import settings


@dataclass
class SimpleItem:
    id: int
    edition_id: int
    title: str | None
    text: str | None
    item_type: str
    page_number: int | None


def main() -> None:
    parser = argparse.ArgumentParser(description="Process a PDF locally and emit items/story groups.")
    parser.add_argument("--pdf", required=True, help="Path to PDF")
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument("--max-pages", type=int, default=None, help="Optional max pages to process")
    parser.add_argument("--ocr", action="store_true", help="Enable OCR if page needs it")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    pdf_processor = create_pdf_processor(settings.min_chars_for_native_text)
    layout = create_layout_analyzer()
    ocr_service = create_ocr_service(settings.ocr_languages) if args.ocr else None

    import fitz  # PyMuPDF

    doc = fitz.open(str(pdf_path))
    pages_out = []
    items_out = []
    item_id = 1

    total_pages = len(doc)
    limit = min(total_pages, args.max_pages) if args.max_pages else total_pages

    for page_index in range(limit):
        page_data = pdf_processor.get_page_data(doc, page_index)
        if page_data.get("needs_ocr") and ocr_service and ocr_service.is_available():
            image_bytes = pdf_processor.get_page_image(str(pdf_path), page_index, dpi=settings.ocr_image_dpi)
            ocr_result = ocr_service.extract_text_with_boxes(
                image_bytes,
                preprocess=settings.ocr_preprocess,
                psm=settings.ocr_psm,
                conf_threshold=settings.ocr_confidence_threshold,
            )
            page_data["extracted_text"] = ocr_result["text"]
            page_data["text_blocks"].extend(ocr_result["text_blocks"])
            page_data["ocr_meta"] = {
                "avg_confidence": ocr_result.get("avg_confidence"),
                "word_count": ocr_result.get("word_count"),
                "psm": ocr_result.get("psm"),
                "preprocess": ocr_result.get("preprocess"),
                "engine": ocr_result.get("engine"),
            }

        page_data = layout.analyze_page(page_data)
        pages_out.append(page_data)

        for item in page_data.get("extracted_items", []):
            items_out.append(
                {
                    "id": item_id,
                    "page_number": page_data.get("page_number"),
                    **item,
                }
            )
            item_id += 1

    simple_items = [
        SimpleItem(
            id=item["id"],
            edition_id=0,
            title=item.get("title"),
            text=item.get("text"),
            item_type=item.get("item_type"),
            page_number=item.get("page_number"),
        )
        for item in items_out
    ]
    story_groups = build_story_groups(simple_items)
    groups_out = [
        {
            "group_id": group.group_id,
            "title": group.title,
            "pages": group.pages,
            "item_ids": group.item_ids,
            "excerpt": group.excerpt,
        }
        for group in story_groups
    ]

    output = {
        "pdf": str(pdf_path),
        "pages": pages_out,
        "items": items_out,
        "story_groups": groups_out,
    }
    Path(args.out).write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {len(pages_out)} pages, {len(items_out)} items, {len(groups_out)} story groups -> {args.out}")


if __name__ == "__main__":
    main()
