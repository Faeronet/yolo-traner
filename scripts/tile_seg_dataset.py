#!/usr/bin/env python3
"""Slice the full-page segmentation dataset into tiles.

Reads:
  data/datasets/drawing_seg/{images,labels}/{train,val,test}/

Writes:
  data/datasets/drawing_seg_tiles/{images,labels}/{train,val,test}/
  data/datasets/drawing_seg_tiles/data.yaml

Tile geometry comes from ``configs/train_drawing_seg.yaml`` (``tile_size``,
``overlap``).
"""

from __future__ import annotations

from pathlib import Path

from tqdm import tqdm

from yolo_train.config import PATHS, read_yaml
from yolo_train.tiling import tile_image_and_labels
from yolo_train.yolo_formats import write_seg_data_yaml

SPLITS = ("train", "val", "test")


def main() -> int:
    PATHS.ensure_all()

    src_root = PATHS.dataset_drawing_seg
    dst_root = PATHS.dataset_drawing_seg_tiles

    train_cfg = read_yaml(PATHS.configs / "train_drawing_seg.yaml")
    tile_size = int(train_cfg.get("tile_size", 1024))
    overlap = int(train_cfg.get("overlap", 128))

    labels_cfg = read_yaml(PATHS.configs / "labels_drawing_seg.yaml")
    class_names = [c["name"] for c in labels_cfg.get("classes", [])]

    if not (src_root / "data.yaml").exists():
        print(f"Source dataset not found at {src_root}. Run build-seg-dataset first.")
        return 0

    total = 0
    for split in SPLITS:
        img_dir = src_root / "images" / split
        lbl_dir = src_root / "labels" / split
        if not img_dir.exists():
            continue
        out_img = dst_root / "images" / split
        out_lbl = dst_root / "labels" / split
        out_img.mkdir(parents=True, exist_ok=True)
        out_lbl.mkdir(parents=True, exist_ok=True)

        images = sorted(p for p in img_dir.iterdir() if p.is_file())
        for img in tqdm(images, desc=f"tiling {split}"):
            label = lbl_dir / (img.stem + ".txt")
            if not label.exists():
                continue
            tiles = tile_image_and_labels(
                img,
                label,
                out_img,
                out_lbl,
                tile_size=tile_size,
                overlap=overlap,
                min_polygons_per_tile=1,
            )
            total += len(tiles)

    yaml_path = dst_root / "data.yaml"
    write_seg_data_yaml(yaml_path, dataset_root=dst_root, class_names=class_names)
    print(f"Generated {total} tile(s). data.yaml: {yaml_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
