from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, help="Path to PDF")
    parser.add_argument("--out-dir", required=True, help="Output directory for images")
    parser.add_argument("--pages-json", required=True, help="Output pages.json")
    parser.add_argument("--dpi", type=int, default=350)
    parser.add_argument("--format", default="png", choices=["png", "jpg", "jpeg"])
    parser.add_argument("--first-page", type=int, default=None)
    parser.add_argument("--last-page", type=int, default=None)
    parser.add_argument("--poppler-path", default=None)
    args = parser.parse_args()

    try:
        from pdf2image import convert_from_path
        use_pdf2image = True
    except Exception:
        use_pdf2image = False

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pages = []
    if use_pdf2image:
        images = convert_from_path(
            args.pdf,
            dpi=args.dpi,
            first_page=args.first_page,
            last_page=args.last_page,
            fmt=args.format,
            poppler_path=args.poppler_path,
        )
        start_num = args.first_page or 1
        for idx, img in enumerate(images, start=start_num):
            file_name = out_dir / f"page_{idx:03d}.{args.format}"
            img.save(file_name)
            width, height = img.size
            pages.append(
                {
                    "number": idx,
                    "width": width,
                    "height": height,
                    "image_path": str(file_name),
                    "blocks": [],
                }
            )
    else:
        try:
            import fitz  # PyMuPDF
        except Exception as exc:
            raise SystemExit(
                "pdf2image is not installed and PyMuPDF is unavailable. "
                "Install pdf2image or PyMuPDF."
            ) from exc
        doc = fitz.open(args.pdf)
        start = (args.first_page or 1) - 1
        end = (args.last_page or doc.page_count) - 1
        for page_index in range(start, end + 1):
            page = doc.load_page(page_index)
            pix = page.get_pixmap(dpi=args.dpi, colorspace=fitz.csRGB, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_num = page_index + 1
            file_name = out_dir / f"page_{page_num:03d}.{args.format}"
            img.save(file_name)
            pages.append(
                {
                    "number": page_num,
                    "width": pix.width,
                    "height": pix.height,
                    "image_path": str(file_name),
                    "blocks": [],
                }
            )

    Path(args.pages_json).write_text(json.dumps(pages, indent=2))
    print(f"Wrote {len(pages)} pages -> {args.pages_json}")


if __name__ == "__main__":
    main()
