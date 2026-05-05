"""Verify that model packages obey the strict whitelist/blacklist."""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest
import yaml

from yolo_train import packaging
from yolo_train.config import PATHS


def _seed_current(model_id: str, files: dict[str, bytes]) -> Path:
    if model_id == "page_router":
        target = PATHS.registry_page_router / "current"
    else:
        target = PATHS.registry_drawing_segmenter / "current"
    if target.exists():
        for p in target.rglob("*"):
            if p.is_file():
                p.unlink()
    target.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        f = target / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
    return target


def _cleanup_packages() -> None:
    if PATHS.model_packages.exists():
        for p in PATHS.model_packages.iterdir():
            if p.is_file():
                p.unlink()


def test_package_contains_only_whitelisted_files() -> None:
    files_pr = {
        "best.pt": b"\x00",
        "best.onnx": b"\x00",
        "labels.txt": b"detail_drawing\nassembly_drawing\nspecification_sheet\nbad_scan\nunknown\n",
        "labels.yaml": yaml.safe_dump({"classes": []}).encode("utf-8"),
        "metadata.yaml": yaml.safe_dump({"model_id": "page_router"}).encode("utf-8"),
        "model_manifest.json": json.dumps({"model_id": "page_router"}).encode("utf-8"),
        "metrics.json": b"{}",
        "train_config_used.yaml": yaml.safe_dump({"model": "yolo11s-cls.pt"}).encode("utf-8"),
        "dataset_ref.json": json.dumps({"task": "classification"}).encode("utf-8"),
        "val_report.md": b"# val\n",
        "README.md": b"# pr\n",
        # Forbidden file that must NOT end up in the package:
        "train_batch0.jpg": b"\xff\xd8\xff",
    }
    files_ds = {
        "best.pt": b"\x00",
        "best.onnx": b"\x00",
        "data.yaml": yaml.safe_dump({"names": []}).encode("utf-8"),
        "labels.txt": b"visible_geometry\nhidden_geometry\ncenterline\ndimension_graphics\ntext\nhatch\nbreak_symbol\nframe_titleblock\nstamp_signature\nnoise\n",
        "labels.yaml": yaml.safe_dump({"classes": []}).encode("utf-8"),
        "metadata.yaml": yaml.safe_dump({"model_id": "drawing_segmenter"}).encode("utf-8"),
        "model_manifest.json": json.dumps({"model_id": "drawing_segmenter"}).encode("utf-8"),
        "metrics.json": b"{}",
        "train_config_used.yaml": yaml.safe_dump({"model": "yolo11m-seg.pt"}).encode("utf-8"),
        "dataset_ref.json": json.dumps({"task": "segmentation"}).encode("utf-8"),
        "val_report.md": b"# val\n",
        "README.md": b"# ds\n",
    }
    _seed_current("page_router", files_pr)
    _seed_current("drawing_segmenter", files_ds)
    _cleanup_packages()

    pr = packaging.build_model_package("page_router", "vTEST")
    ds = packaging.build_model_package("drawing_segmenter", "vTEST")

    with tarfile.open(pr.archive_path, "r:gz") as tar:
        names_pr = sorted(m.name for m in tar.getmembers())
    with tarfile.open(ds.archive_path, "r:gz") as tar:
        names_ds = sorted(m.name for m in tar.getmembers())

    assert all(n.startswith("page_router/") for n in names_pr)
    assert all(n.startswith("drawing_segmenter/") for n in names_ds)
    assert "page_router/best.pt" in names_pr
    assert "drawing_segmenter/best.pt" in names_ds
    # Forbidden file must be absent
    assert all(not n.endswith(".jpg") for n in names_pr)
    # Whitelist enforcement: nothing else sneaks in
    extras = set(names_pr) - {
        "page_router/best.pt",
        "page_router/best.onnx",
        "page_router/labels.txt",
        "page_router/labels.yaml",
        "page_router/metadata.yaml",
        "page_router/model_manifest.json",
        "page_router/metrics.json",
        "page_router/train_config_used.yaml",
        "page_router/dataset_ref.json",
        "page_router/val_report.md",
        "page_router/README.md",
    }
    assert not extras, f"Unexpected files in page_router package: {extras}"


def test_package_fails_when_no_current(tmp_path: Path) -> None:
    # Wipe currents to force failure
    for model in ("page_router", "drawing_segmenter"):
        if model == "page_router":
            target = PATHS.registry_page_router / "current"
        else:
            target = PATHS.registry_drawing_segmenter / "current"
        if target.exists():
            for p in list(target.rglob("*")):
                if p.is_file():
                    p.unlink()
            target.rmdir()

    with pytest.raises(FileNotFoundError):
        packaging.build_model_package("page_router", "vNEVER")
