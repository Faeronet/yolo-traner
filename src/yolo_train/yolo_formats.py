"""YOLO classification / segmentation dataset format helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import yaml


# -----------------------------------------------------------------------------
# Classification
# -----------------------------------------------------------------------------
def write_classification_root(root: Path | str, class_names: Sequence[str]) -> Path:
    """Create ``root/{train,val,test}/<class>/`` skeleton for YOLO -cls training."""
    root = Path(root)
    for split in ("train", "val", "test"):
        for name in class_names:
            (root / split / name).mkdir(parents=True, exist_ok=True)
    return root


# -----------------------------------------------------------------------------
# Segmentation
# -----------------------------------------------------------------------------
def write_seg_data_yaml(
    out_path: Path | str,
    *,
    dataset_root: Path | str,
    class_names: Sequence[str],
    train_dir: str = "images/train",
    val_dir: str = "images/val",
    test_dir: str = "images/test",
) -> Path:
    """Write Ultralytics ``data.yaml`` for a segmentation dataset."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "path": str(Path(dataset_root).resolve()),
        "train": train_dir,
        "val": val_dir,
        "test": test_dir,
        "names": {i: n for i, n in enumerate(class_names)},
    }
    with out_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    return out_path


def parse_yolo_seg_label(label_path: Path | str) -> list[tuple[int, list[float]]]:
    """Read a YOLO segmentation label file.

    Returns a list of ``(class_id, [x1, y1, x2, y2, ...])`` tuples in
    normalized image coordinates.
    """
    label_path = Path(label_path)
    out: list[tuple[int, list[float]]] = []
    if not label_path.exists():
        return out
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) < 7:  # cls + at least 3 (x,y) pairs
            continue
        try:
            cls = int(parts[0])
            coords = [float(x) for x in parts[1:]]
        except ValueError:
            continue
        if len(coords) % 2 != 0:
            continue
        out.append((cls, coords))
    return out


def write_yolo_seg_label(
    label_path: Path | str,
    items: Sequence[tuple[int, Sequence[float]]],
) -> Path:
    """Write a YOLO segmentation label file."""
    label_path = Path(label_path)
    label_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for cls, coords in items:
        if len(coords) < 6 or len(coords) % 2 != 0:
            continue
        line = " ".join([str(int(cls)), *(f"{c:.6f}" for c in coords)])
        lines.append(line)
    label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return label_path
