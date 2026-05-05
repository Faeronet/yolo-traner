"""Verify YOLO seg label parsing/writing and dataset validation contracts."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from yolo_train.validation import (
    validate_classification_dataset,
    validate_segmentation_dataset,
)
from yolo_train.yolo_formats import (
    parse_yolo_seg_label,
    write_classification_root,
    write_seg_data_yaml,
    write_yolo_seg_label,
)


def _png(path: Path, *, size: tuple[int, int] = (32, 32)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (255, 255, 255)).save(path)
    return path


def test_seg_label_round_trip(tmp_path: Path) -> None:
    label = tmp_path / "x.txt"
    items = [(0, [0.1, 0.1, 0.9, 0.1, 0.9, 0.9, 0.1, 0.9])]
    write_yolo_seg_label(label, items)
    parsed = parse_yolo_seg_label(label)
    assert parsed == items


def test_seg_label_rejects_too_short(tmp_path: Path) -> None:
    label = tmp_path / "x.txt"
    label.write_text("0 0.1 0.1\n", encoding="utf-8")
    assert parse_yolo_seg_label(label) == []


def test_validate_classification_ok(tmp_path: Path) -> None:
    classes = ["a", "b"]
    write_classification_root(tmp_path, classes)
    _png(tmp_path / "train" / "a" / "1.png")
    _png(tmp_path / "val" / "a" / "1.png")
    _png(tmp_path / "test" / "b" / "1.png")
    rep = validate_classification_dataset(tmp_path, classes)
    assert rep.to_dict()["ok"] is True
    assert rep.splits == {"train": 1, "val": 1, "test": 1}


def test_validate_segmentation_catches_invalid_class(tmp_path: Path) -> None:
    classes = ["a", "b"]
    write_seg_data_yaml(
        tmp_path / "data.yaml", dataset_root=tmp_path, class_names=classes
    )
    img_train = tmp_path / "images" / "train"
    img_val = tmp_path / "images" / "val"
    img_test = tmp_path / "images" / "test"
    lbl_train = tmp_path / "labels" / "train"
    lbl_val = tmp_path / "labels" / "val"
    lbl_test = tmp_path / "labels" / "test"
    for d in (img_train, img_val, img_test, lbl_train, lbl_val, lbl_test):
        d.mkdir(parents=True, exist_ok=True)

    _png(img_train / "ok.png")
    write_yolo_seg_label(lbl_train / "ok.txt", [(0, [0.1] * 6)])
    _png(img_val / "bad.png")
    write_yolo_seg_label(lbl_val / "bad.txt", [(99, [0.1] * 6)])
    _png(img_test / "ok.png")
    write_yolo_seg_label(lbl_test / "ok.txt", [(1, [0.1] * 6)])

    rep = validate_segmentation_dataset(tmp_path, classes)
    assert any("Invalid class id" in err for err in rep.errors)
