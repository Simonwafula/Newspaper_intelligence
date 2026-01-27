from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Label Studio JSON export")
    parser.add_argument("--out", required=True, help="Output COCO JSON")
    parser.add_argument("--image-root", default=".", help="Root dir for images")
    parser.add_argument("--label-list", default="", help="Path to label list text file")
    parser.add_argument("--label-map-out", default="", help="Write label map json (0-based)")
    args = parser.parse_args()

    tasks = json.loads(Path(args.input).read_text())
    image_root = Path(args.image_root)

    categories: Dict[str, int] = {}
    label_order: List[str] = []
    if args.label_list:
        label_order = [line.strip() for line in Path(args.label_list).read_text().splitlines() if line.strip()]
        for idx, name in enumerate(label_order, start=1):
            categories[name] = idx
    images = []
    annotations = []
    ann_id = 1

    for idx, task in enumerate(tasks, start=1):
        img_path = task.get("data", {}).get("image")
        if not img_path:
            continue
        img_file = image_root / Path(img_path).name if not Path(img_path).is_file() else Path(img_path)
        with Image.open(img_file) as img:
            width, height = img.size

        images.append(
            {
                "id": idx,
                "file_name": str(img_file),
                "width": width,
                "height": height,
            }
        )

        for ann in task.get("annotations", []):
            for res in ann.get("result", []):
                if res.get("type") != "rectanglelabels":
                    continue
                labels = res.get("value", {}).get("rectanglelabels", [])
                if not labels:
                    continue
                label = labels[0]
                if label not in categories:
                    categories[label] = len(categories) + 1
                x = res["value"]["x"] / 100.0 * width
                y = res["value"]["y"] / 100.0 * height
                w = res["value"]["width"] / 100.0 * width
                h = res["value"]["height"] / 100.0 * height

                annotations.append(
                    {
                        "id": ann_id,
                        "image_id": idx,
                        "category_id": categories[label],
                        "bbox": [x, y, w, h],
                        "area": w * h,
                        "iscrowd": 0,
                    }
                )
                ann_id += 1

    coco = {
        "images": images,
        "annotations": annotations,
        "categories": [
            {"id": cid, "name": name, "supercategory": "layout"}
            for name, cid in sorted(categories.items(), key=lambda kv: kv[1])
        ],
    }
    Path(args.out).write_text(json.dumps(coco, indent=2))
    print(f"Wrote COCO with {len(images)} images and {len(annotations)} annotations")

    if args.label_map_out:
        if not label_order:
            label_order = [name for name, _ in sorted(categories.items(), key=lambda kv: kv[1])]
        label_map = {str(idx): name for idx, name in enumerate(label_order)}
        Path(args.label_map_out).write_text(json.dumps(label_map, indent=2))
        print(f"Wrote label map -> {args.label_map_out}")


if __name__ == "__main__":
    main()
