from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
from PIL import Image

from pipeline.core.io import load_pages
from pipeline.core.schemas import BBox, Block


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", required=True, help="Path to pages.json")
    parser.add_argument("--out", required=True, help="Output pages.json")
    parser.add_argument("--config", required=True, help="Detectron2 config yaml")
    parser.add_argument("--weights", required=True, help="Model weights path")
    parser.add_argument("--label-map", required=True, help="JSON mapping id->label")
    parser.add_argument("--score-thresh", type=float, default=0.5)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    try:
        import layoutparser as lp
    except Exception as exc:
        raise SystemExit(
            "layoutparser is not installed. Install with: pip install layoutparser"
        ) from exc

    label_map: Dict[int, str] = {}
    label_map_raw = json.loads(Path(args.label_map).read_text())
    for key, value in label_map_raw.items():
        label_map[int(key)] = str(value)

    model = lp.Detectron2LayoutModel(
        config_path=args.config,
        model_path=args.weights,
        label_map=label_map,
        extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", args.score_thresh],
        device=args.device,
    )

    pages = load_pages(args.pages)
    for page in pages:
        if not page.image_path:
            continue
        image = np.array(Image.open(page.image_path).convert("RGB"))
        layout = model.detect(image)
        blocks: List[Block] = []
        for idx, region in enumerate(layout):
            x1, y1, x2, y2 = region.block.coordinates
            blocks.append(
                Block(
                    id=f"p{page.number}_b{idx:03d}",
                    type=str(region.type),
                    bbox=BBox(float(x1), float(y1), float(x2), float(y2)),
                    score=float(region.score) if region.score is not None else None,
                    text="",
                    words=[],
                    page=page.number,
                    column=None,
                )
            )
        if args.overwrite or not page.blocks:
            page.blocks = blocks
        else:
            page.blocks.extend(blocks)

    Path(args.out).write_text(json.dumps([p.to_dict() for p in pages], indent=2))
    print(f"Wrote layout blocks -> {args.out}")


if __name__ == "__main__":
    main()
