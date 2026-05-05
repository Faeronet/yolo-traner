#!/usr/bin/env python3
"""Validate built datasets and produce reports.

Outputs:
  data/reports/dataset_validation.json
  data/reports/dataset_validation.md
  data/reports/class_distribution.json
  data/reports/class_distribution.md
"""

from __future__ import annotations

import sys

from yolo_train.config import PATHS, read_yaml
from yolo_train.reports import (
    class_distribution_table,
    errors_warnings_section,
    write_json,
    write_markdown_report,
)
from yolo_train.splitting import assert_no_leakage
from yolo_train.validation import (
    validate_classification_dataset,
    validate_segmentation_dataset,
)


def main() -> int:
    PATHS.ensure_all()

    page_cls_labels = [c["name"] for c in read_yaml(PATHS.configs / "labels_page_cls.yaml").get("classes", [])]
    seg_labels = [c["name"] for c in read_yaml(PATHS.configs / "labels_drawing_seg.yaml").get("classes", [])]

    page_cls_report = validate_classification_dataset(PATHS.dataset_page_cls, page_cls_labels)
    seg_report_full = validate_segmentation_dataset(PATHS.dataset_drawing_seg, seg_labels)
    seg_report_tiles = validate_segmentation_dataset(PATHS.dataset_drawing_seg_tiles, seg_labels)

    # Leakage protection
    page_cls_split = list(_iter_split_csv(PATHS.splits / "page_cls_split.csv"))
    seg_split = list(_iter_split_csv(PATHS.splits / "drawing_seg_split.csv"))
    leakage_errors: list[str] = []
    try:
        assert_no_leakage(_group_split(page_cls_split), group_key="page_id")
    except ValueError as exc:
        leakage_errors.append(f"page_cls: {exc}")
    try:
        assert_no_leakage(_group_split(seg_split), group_key="page_id")
    except ValueError as exc:
        leakage_errors.append(f"drawing_seg: {exc}")

    payload = {
        "page_router": page_cls_report.to_dict(),
        "drawing_segmenter_full": seg_report_full.to_dict(),
        "drawing_segmenter_tiles": seg_report_tiles.to_dict(),
        "leakage_errors": leakage_errors,
        "ok": (
            page_cls_report.to_dict()["ok"]
            and seg_report_full.to_dict()["ok"]
            and seg_report_tiles.to_dict()["ok"]
            and not leakage_errors
        ),
    }
    write_json(PATHS.reports / "dataset_validation.json", payload)

    md_sections = {
        "page_router (classification)": "\n\n".join(
            [
                f"Splits: {page_cls_report.splits}",
                class_distribution_table(page_cls_report.class_counts),
                errors_warnings_section(page_cls_report.errors, page_cls_report.warnings),
            ]
        ),
        "drawing_segmenter (full pages)": "\n\n".join(
            [
                f"Splits: {seg_report_full.splits}",
                class_distribution_table(seg_report_full.class_counts),
                errors_warnings_section(seg_report_full.errors, seg_report_full.warnings),
            ]
        ),
        "drawing_segmenter (tiled)": "\n\n".join(
            [
                f"Splits: {seg_report_tiles.splits}",
                class_distribution_table(seg_report_tiles.class_counts),
                errors_warnings_section(seg_report_tiles.errors, seg_report_tiles.warnings),
            ]
        ),
        "Leakage check": "\n".join(f"- {e}" for e in leakage_errors) if leakage_errors else "OK",
    }
    write_markdown_report(PATHS.reports / "dataset_validation.md", "Dataset validation", md_sections)

    distrib = {
        "page_router": page_cls_report.class_counts,
        "drawing_segmenter_full": seg_report_full.class_counts,
        "drawing_segmenter_tiles": seg_report_tiles.class_counts,
    }
    write_json(PATHS.reports / "class_distribution.json", distrib)
    write_markdown_report(
        PATHS.reports / "class_distribution.md",
        "Class distribution",
        {
            "page_router": class_distribution_table(page_cls_report.class_counts),
            "drawing_segmenter (full)": class_distribution_table(seg_report_full.class_counts),
            "drawing_segmenter (tiles)": class_distribution_table(seg_report_tiles.class_counts),
        },
    )

    if not payload["ok"]:
        print("Dataset validation reported errors. See data/reports/", file=sys.stderr)
        return 1
    print("Dataset validation OK. Reports under data/reports/.")
    return 0


def _iter_split_csv(path):
    from yolo_train.inventory import read_csv

    return read_csv(path)


def _group_split(rows):
    out: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    for r in rows:
        s = r.get("split")
        if s in out:
            out[s].append(r)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
