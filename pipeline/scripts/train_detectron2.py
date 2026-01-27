from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Detectron2 config yaml")
    parser.add_argument("--output", required=True, help="Output dir")
    parser.add_argument("--train-json", required=True, help="COCO train json")
    parser.add_argument("--val-json", required=True, help="COCO val json")
    parser.add_argument("--image-root", required=True, help="Image root directory")
    parser.add_argument("--train-name", default="newspaper_train")
    parser.add_argument("--val-name", default="newspaper_val")
    parser.add_argument("--num-classes", type=int, default=None)
    parser.add_argument("--weights", default=None, help="Override model weights")
    parser.add_argument("--max-iter", type=int, default=None)
    parser.add_argument("--base-lr", type=float, default=None)
    args = parser.parse_args()

    try:
        from detectron2.config import get_cfg
        from detectron2.engine import DefaultTrainer
        from detectron2.data.datasets import register_coco_instances
    except Exception as exc:
        raise SystemExit(
            "Detectron2 is not installed. Install detectron2 first, then re-run.\n"
            "Example: pip install 'git+https://github.com/facebookresearch/detectron2.git'"
        ) from exc

    register_coco_instances(args.train_name, {}, args.train_json, args.image_root)
    register_coco_instances(args.val_name, {}, args.val_json, args.image_root)

    cfg = get_cfg()
    cfg.merge_from_file(args.config)
    cfg.OUTPUT_DIR = args.output
    cfg.DATASETS.TRAIN = (args.train_name,)
    cfg.DATASETS.TEST = (args.val_name,)
    if args.weights:
        cfg.MODEL.WEIGHTS = args.weights
    if args.num_classes is not None:
        cfg.MODEL.ROI_HEADS.NUM_CLASSES = args.num_classes
    if args.max_iter is not None:
        cfg.SOLVER.MAX_ITER = args.max_iter
    if args.base_lr is not None:
        cfg.SOLVER.BASE_LR = args.base_lr

    trainer = DefaultTrainer(cfg)
    trainer.resume_or_load(resume=False)
    trainer.train()


if __name__ == "__main__":
    main()
