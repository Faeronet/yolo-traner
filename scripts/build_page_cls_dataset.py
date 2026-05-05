#!/usr/bin/env python3
"""Build YOLO classification dataset for page_router from CVAT export.

Expected input: ``data/cvat_exports/page_classification/`` containing CVAT
"CVAT for images 1.1" export(s) (zip or already-unpacked XML + images).

For each labeled image we pick a single tag (the 5 page classes). Files are
copied into ``data/datasets/page_cls/{train,val,test}/<class>/``.

Splitting is grouped by source document stem to avoid leakage.
"""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

from yolo_train.config import PATHS, read_yaml
from yolo_train.inventory import PAGE_LABELS_FIELDS, SPLIT_FIELDS, write_csv
from yolo_train.splitting import split_by_group
from yolo_train.yolo_formats import write_classification_root


def _unzip_exports(root: Path) -> list[Path]:
    """Unzip every *.zip under ``root`` into a sibling directory."""
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


def _parse_cvat_xml(xml_path: Path, allowed: set[str]) -> dict[str, str]:
    """Return ``{image_relpath: chosen_class}`` from a CVAT-for-images XML."""
    out: dict[str, str] = {}
    if not xml_path.exists():
        return out
    tree = ET.parse(xml_path)
    for img in tree.getroot().findall("image"):
        name = img.get("name")
        if not name:
            continue
        chosen: str | None = None
        for tag in img.findall("tag"):
            label = tag.get("label")
            if label and label in allowed:
                chosen = label
                break
        if chosen is None:
            for box in img.findall("box"):
                label = box.get("label")
                if label and label in allowed:
                    chosen = label
                    break
        if chosen is not None:
            out[name] = chosen
    return out


def _source_stem(image_name: str) -> str:
    stem = Path(image_name).stem
    if "__" in stem:
        stem = stem.split("__", 1)[-1]
    if "_p" in stem and stem.rsplit("_p", 1)[-1].isdigit():
        stem = stem.rsplit("_p", 1)[0]
    return stem


def main() -> int:
    PATHS.ensure_all()
    labels_cfg = read_yaml(PATHS.configs / "labels_page_cls.yaml")
    class_names = [c["name"] for c in labels_cfg.get("classes", [])]
    allowed = set(class_names)

    write_classification_root(PATHS.dataset_page_cls, class_names)

    export_root = PATHS.cvat_export_page_cls
    exports = _unzip_exports(export_root)
    if not exports:
        print(
            f"No CVAT exports found under {export_root}. "
            "Place an export there (see docs/annotation_guide.md) and rerun."
        )
        return 0

    items: list[dict] = []
    for export_dir in exports:
        xml_path = export_dir / "annotations.xml"
        labels = _parse_cvat_xml(xml_path, allowed)
        for image_name, cls in labels.items():
            img_src = export_dir / "images" / image_name
            if not img_src.exists():
                img_src = export_dir / image_name
            if not img_src.exists():
                continue
            items.append(
                {
                    "image": str(img_src),
                    "image_name": Path(image_name).name,
                    "class": cls,
                    "group": _source_stem(image_name),
                }
            )

    if not items:
        print("CVAT export found but no labeled images recognized; aborting.")
        return 0

    splits = split_by_group(items, group_key="group", train=0.8, val=0.1, test=0.1, salt="page_cls")

    label_rows: list[dict] = []
    split_rows: list[dict] = []
    counts: Counter[str] = Counter()
    for split, rows in splits.items():
        for row in rows:
            target_dir = PATHS.dataset_page_cls / split / row["class"]
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / row["image_name"]
            shutil.copy2(row["image"], target)
            counts[f"{split}/{row['class']}"] += 1
            page_id = Path(row["image_name"]).stem.split("__", 1)[0]
            label_rows.append(
                {
                    "page_id": page_id,
                    "label": row["class"],
                    "source_task": "cvat",
                    "annotator": "",
                    "annotated_at": "",
                }
            )
            split_rows.append({"page_id": page_id, "split": split})

    write_csv(PATHS.inventory / "page_labels.csv", PAGE_LABELS_FIELDS, label_rows)
    write_csv(PATHS.splits / "page_cls_split.csv", SPLIT_FIELDS, split_rows)

    print(f"Built {sum(counts.values())} labeled images:")
    for k in sorted(counts):
        print(f"  {k}: {counts[k]}")
    print(f"Dataset ready at: {PATHS.dataset_page_cls}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
