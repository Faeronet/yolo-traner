#!/usr/bin/env python3
"""Build YOLO segmentation dataset for drawing_segmenter from CVAT export.

Expected input: ``data/cvat_exports/drawing_segmentation/`` containing
"Ultralytics YOLO Segmentation 1.0" export(s) (zip or directory).

Each export already comes as YOLO segmentation layout with ``data.yaml``,
``images/`` and ``labels/``. We:

1. Merge images+labels from all exports.
2. Verify class id order matches ``configs/labels_drawing_seg.yaml``.
3. Split by source document stem into train/val/test.
4. Write ``data/datasets/drawing_seg/{images,labels}/{train,val,test}/``
   and ``data/datasets/drawing_seg/data.yaml``.
"""

from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

import yaml

from yolo_train.config import PATHS, read_yaml
from yolo_train.inventory import SPLIT_FIELDS, write_csv
from yolo_train.splitting import split_by_group
from yolo_train.yolo_formats import write_seg_data_yaml


def _unzip_exports(root: Path) -> list[Path]:
    out_dirs: list[Path] = []
    for zip_path in sorted(root.glob("*.zip")):
        target = zip_path.with_suffix("")
        if not target.exists():
            target.mkdir(parents=True)
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(target)
        out_dirs.append(target)
    for d in root.iterdir():
        if d.is_dir() and d not in out_dirs:
            out_dirs.append(d)
    return sorted(set(out_dirs))


def _check_class_order(export_dir: Path, expected: list[str]) -> None:
    data_yaml = next(export_dir.rglob("data.yaml"), None)
    if not data_yaml:
        return
    cfg = read_yaml(data_yaml)
    names = cfg.get("names")
    if isinstance(names, dict):
        ordered = [names[i] for i in sorted(names)]
    elif isinstance(names, list):
        ordered = list(names)
    else:
        return
    if ordered != expected:
        raise RuntimeError(
            f"Class order mismatch in {data_yaml}: {ordered} != {expected}. "
            "Re-export from CVAT with the canonical label order."
        )


def _source_stem(image_name: str) -> str:
    stem = Path(image_name).stem
    if "__" in stem:
        stem = stem.split("__", 1)[-1]
    if "_p" in stem and stem.rsplit("_p", 1)[-1].isdigit():
        stem = stem.rsplit("_p", 1)[0]
    return stem


def _gather_pairs(export_dir: Path) -> list[dict]:
    pairs: list[dict] = []
    for image_path in export_dir.rglob("*"):
        if not image_path.is_file():
            continue
        if image_path.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            continue
        # Map to corresponding label file.
        rel = image_path.relative_to(export_dir)
        parts = rel.parts
        if not parts or parts[0] != "images":
            continue
        rel_label = Path("labels", *parts[1:]).with_suffix(".txt")
        label_path = export_dir / rel_label
        if not label_path.exists():
            continue
        pairs.append(
            {
                "image": image_path,
                "label": label_path,
                "name": image_path.name,
                "group": _source_stem(image_path.name),
            }
        )
    return pairs


def main() -> int:
    PATHS.ensure_all()
    labels_cfg = read_yaml(PATHS.configs / "labels_drawing_seg.yaml")
    class_names = [c["name"] for c in labels_cfg.get("classes", [])]

    export_root = PATHS.cvat_export_drawing_seg
    exports = _unzip_exports(export_root)
    if not exports:
        print(
            f"No CVAT exports found under {export_root}. "
            "Place an Ultralytics YOLO Segmentation export there and rerun."
        )
        return 0

    pairs: list[dict] = []
    for ex in exports:
        try:
            _check_class_order(ex, class_names)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        pairs.extend(_gather_pairs(ex))

    if not pairs:
        print("No image/label pairs recognized in CVAT exports; aborting.")
        return 0

    splits = split_by_group(pairs, group_key="group", train=0.8, val=0.1, test=0.1, salt="drawing_seg")

    root = PATHS.dataset_drawing_seg
    for split in ("train", "val", "test"):
        (root / "images" / split).mkdir(parents=True, exist_ok=True)
        (root / "labels" / split).mkdir(parents=True, exist_ok=True)

    split_rows: list[dict] = []
    counts: dict[str, int] = {"train": 0, "val": 0, "test": 0}
    for split, rows in splits.items():
        for row in rows:
            img_dst = root / "images" / split / row["name"]
            lbl_dst = root / "labels" / split / (Path(row["name"]).stem + ".txt")
            shutil.copy2(row["image"], img_dst)
            shutil.copy2(row["label"], lbl_dst)
            counts[split] += 1
            page_id = Path(row["name"]).stem.split("__", 1)[0]
            split_rows.append({"page_id": page_id, "split": split})

    yaml_path = root / "data.yaml"
    write_seg_data_yaml(yaml_path, dataset_root=root, class_names=class_names)
    write_csv(PATHS.splits / "drawing_seg_split.csv", SPLIT_FIELDS, split_rows)

    print(
        f"Segmentation dataset built: train={counts['train']}, val={counts['val']}, test={counts['test']}"
    )
    print(f"data.yaml: {yaml_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
