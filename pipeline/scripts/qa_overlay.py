from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from pipeline.core.io import load_pages


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", required=True, help="Path to pages.json")
    parser.add_argument("--out", required=True, help="Output dir for overlays")
    args = parser.parse_args()

    pages = load_pages(args.pages)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for page in pages:
        if not page.image_path:
            continue
        img = Image.open(page.image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        for block in page.blocks:
            x1, y1, x2, y2 = block.bbox.to_list()
            color = color_for_type(block.type)
            draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
            label = f"{block.type}:{block.id}"
            draw.text((x1 + 2, y1 + 2), label, fill=color)
        out_path = out_dir / f"page_{page.number:03d}.png"
        img.save(out_path)


def color_for_type(t: str) -> str:
    palette = {
        "headline": "#ff6f00",
        "title": "#ff6f00",
        "subhead": "#ffb300",
        "byline": "#e64a19",
        "body": "#1e88e5",
        "caption": "#8e24aa",
        "section": "#43a047",
        "ad": "#546e7a",
    }
    return palette.get(t, "#6d4c41")


if __name__ == "__main__":
    main()
