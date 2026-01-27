# Newspaper Extraction Pipeline

This folder contains a stand-alone pipeline scaffold for PDF newspaper extraction:

1) Render PDF pages to images (not included here)
2) Layout detection -> blocks with bboxes
3) OCR per block -> words + text
4) Ordering + continuation rules
5) Story grouping and JSON output

The Django/Wagtail app in `nextstep/` is not required to run this pipeline.

## Expected input format

`pages.json` should contain a list of pages like:

```json
[
  {
    "number": 1,
    "width": 2550,
    "height": 3300,
    "image_path": "data/pages/001.png",
    "blocks": [
      {
        "id": "p1_b001",
        "type": "headline",
        "bbox": [100, 120, 1200, 260],
        "score": 0.97,
        "text": "Title of the story",
        "words": [
          {"text": "Title", "bbox": [110, 130, 240, 170], "conf": 0.98}
        ],
        "page": 1,
        "column": 0
      }
    ]
  }
]
```

## Run ordering + story linking

```bash
python -m pipeline.scripts.order_and_link --pages data/pages.json --out data/stories.json
```

## Render PDF -> pages.json

```bash
python -m pipeline.scripts.pdf_to_images --pdf data/issue.pdf --out-dir data/images --pages-json data/pages.json --dpi 350
```

## Layout inference

```bash
python -m pipeline.scripts.layout_infer --pages data/pages.json --out data/pages.layout.json --config configs/layout.yaml --weights outputs/model.pth --label-map data/label_map.json --score-thresh 0.5
```

## OCR per block

```bash
python -m pipeline.scripts.ocr_blocks --pages data/pages.layout.json --out data/pages.ocr.json --engine paddle --lang en
```

## Generate QA overlays

```bash
python -m pipeline.scripts.qa_overlay --pages data/pages.json --out outputs/overlays
```

## Label Studio config

Use `labelstudio/label_config.xml` to label layout blocks and story ids.

Convert Label Studio exports to COCO:

```bash
python -m pipeline.scripts.ls_to_coco --input data/labels.json --out data/layout.coco.json --image-root data/images --label-list pipeline/configs/labels.txt --label-map-out data/label_map.json
```

Training entrypoint (Detectron2 must be installed separately):

```bash
python -m pipeline.scripts.train_detectron2 --config pipeline/configs/layout.yaml --output outputs/layout_model --train-json data/layout_train.coco.json --val-json data/layout_val.coco.json --image-root data/images --num-classes 8
```

## Dependencies

Install the pipeline extras in a separate environment to avoid touching the Wagtail app:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r pipeline/requirements.txt
```

`pipeline/requirements.txt` lists common OCR/layout/embedding packages; you can remove any you do not use.

For layout inference you may also need Detectron2 and layoutparser, which are installed separately.
