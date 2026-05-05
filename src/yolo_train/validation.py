"""Dataset integrity / validation."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from PIL import Image

from .yolo_formats import parse_yolo_seg_label

IMG_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")


@dataclass
class ValidationReport:
    dataset: str
    task: str
    splits: dict[str, int] = field(default_factory=dict)
    class_counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "task": self.task,
            "splits": self.splits,
            "class_counts": self.class_counts,
            "errors": self.errors,
            "warnings": self.warnings,
            "ok": not self.errors,
        }


def validate_classification_dataset(root: Path | str, class_names: Sequence[str]) -> ValidationReport:
    """Validate a YOLO -cls layout: ``root/<split>/<class>/*.png``."""
    root = Path(root)
    rep = ValidationReport(dataset=str(root), task="classification")
    expected = set(class_names)

    for split in ("train", "val", "test"):
        split_dir = root / split
        if not split_dir.exists():
            rep.errors.append(f"Missing split directory: {split_dir}")
            continue
        present = {p.name for p in split_dir.iterdir() if p.is_dir()}
        missing = expected - present
        extra = present - expected
        if missing:
            rep.errors.append(f"Missing classes in {split}: {sorted(missing)}")
        if extra:
            rep.warnings.append(f"Unexpected classes in {split}: {sorted(extra)}")

        count = 0
        for cls in expected:
            cls_dir = split_dir / cls
            if not cls_dir.exists():
                continue
            files = [p for p in cls_dir.iterdir() if p.suffix.lower() in IMG_SUFFIXES]
            for f in files:
                try:
                    with Image.open(f) as im:
                        im.verify()
                except Exception as exc:  # noqa: BLE001
                    rep.errors.append(f"Corrupt image {f}: {exc}")
            cnt = len(files)
            count += cnt
            rep.class_counts[f"{split}/{cls}"] = cnt
        rep.splits[split] = count

    return rep


def validate_segmentation_dataset(
    root: Path | str,
    class_names: Sequence[str],
) -> ValidationReport:
    """Validate a YOLO segmentation layout (``images/<split>``, ``labels/<split>``)."""
    root = Path(root)
    rep = ValidationReport(dataset=str(root), task="segmentation")
    n_classes = len(class_names)

    overall_counter: Counter[int] = Counter()

    for split in ("train", "val", "test"):
        img_dir = root / "images" / split
        lbl_dir = root / "labels" / split
        if not img_dir.exists() or not lbl_dir.exists():
            rep.errors.append(f"Missing split dirs for {split}: {img_dir} / {lbl_dir}")
            continue

        images = [p for p in img_dir.rglob("*") if p.is_file() and p.suffix.lower() in IMG_SUFFIXES]
        rep.splits[split] = len(images)

        for img in images:
            label = lbl_dir / (img.stem + ".txt")
            if not label.exists():
                rep.warnings.append(f"Image without label: {img}")
                continue

            try:
                with Image.open(img) as im:
                    im.verify()
            except Exception as exc:  # noqa: BLE001
                rep.errors.append(f"Corrupt image {img}: {exc}")
                continue

            polys = parse_yolo_seg_label(label)
            if not polys:
                rep.warnings.append(f"Empty label file: {label}")
                continue

            for cls, coords in polys:
                if cls < 0 or cls >= n_classes:
                    rep.errors.append(f"Invalid class id {cls} in {label}")
                if any(c < 0 or c > 1 for c in coords):
                    rep.errors.append(f"Out-of-range coordinate in {label}")
                if cls < n_classes:
                    overall_counter[cls] += 1

    for cls_id, name in enumerate(class_names):
        rep.class_counts[name] = overall_counter.get(cls_id, 0)

    return rep


def assert_split_exists(root: Path) -> None:
    """Raise if any of the expected split dirs is missing."""
    for split in ("train", "val", "test"):
        if not (root / split).exists():
            raise FileNotFoundError(f"Missing split dir: {root / split}")
