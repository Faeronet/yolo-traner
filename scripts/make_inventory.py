#!/usr/bin/env python3
"""Stage 4 of `make prepare`: build inventory CSVs.

Writes:
  * data/inventory/files_inventory.csv
  * data/inventory/pages_inventory.csv

Also populates the CVAT shared folders:
  * data/cvat_shared/page_classification/    <- every page (hardlink, fallback to copy)
  * data/cvat_shared/drawing_segmentation/   <- same set; downstream filtering by labels
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from tqdm import tqdm

from yolo_train.config import PATHS, load_env
from yolo_train.image import file_sha256, image_size
from yolo_train.inventory import (
    FILES_FIELDS,
    PAGES_FIELDS,
    write_csv,
)


def _kind_of(p: Path) -> str:
    s = p.suffix.lower()
    if s == ".pdf":
        return "pdf"
    if s in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"):
        return "image"
    if s in (".rar", ".zip", ".7z", ".tar", ".gz", ".bz2", ".xz"):
        return "archive"
    return "other"


def _link_or_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def _write_files_inventory() -> int:
    rows = []
    fid = 0
    for root in (PATHS.raw_archives, PATHS.raw_pdfs, PATHS.raw_images, PATHS.raw_extracted):
        if not root.exists():
            continue
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            fid += 1
            rows.append(
                {
                    "file_id": f"f{fid:06d}",
                    "rel_path": str(p.relative_to(PATHS.root)),
                    "kind": _kind_of(p),
                    "size_bytes": p.stat().st_size,
                    "sha256": file_sha256(p),
                    "source": root.name,
                }
            )
    out = PATHS.inventory / "files_inventory.csv"
    write_csv(out, FILES_FIELDS, rows)
    print(f"Wrote {out} ({len(rows)} files)")
    return len(rows)


def _write_pages_inventory_and_share() -> int:
    rows = []
    pages = sorted(p for p in PATHS.pages_all.iterdir() if p.is_file() and p.suffix.lower() == ".png")
    pid = 0
    for p in tqdm(pages, desc="pages"):
        pid += 1
        try:
            w, h = image_size(p)
        except Exception:  # noqa: BLE001
            w, h = (0, 0)
        page_id = f"p{pid:06d}"
        stem = p.stem
        if "_p" in stem and stem.rsplit("_p", 1)[-1].isdigit():
            source_stem, page_idx_str = stem.rsplit("_p", 1)
            page_idx = int(page_idx_str)
        else:
            source_stem, page_idx = stem, 1

        rows.append(
            {
                "page_id": page_id,
                "source_file_id": "",
                "source_rel_path": source_stem,
                "page_index": page_idx,
                "width": w,
                "height": h,
                "rel_path": str(p.relative_to(PATHS.root)),
                "sha256": file_sha256(p),
            }
        )

        # Stage into CVAT shared folders. Both projects use the full set
        # of pages; they're filtered later per project (page_router by tag,
        # drawing_segmenter by polygon label).
        share_name = f"{page_id}__{stem}.png"
        _link_or_copy(p, PATHS.cvat_shared_page_cls / share_name)
        _link_or_copy(p, PATHS.cvat_shared_drawing_seg / share_name)

    out = PATHS.inventory / "pages_inventory.csv"
    write_csv(out, PAGES_FIELDS, rows)
    print(f"Wrote {out} ({len(rows)} pages)")
    print(f"Staged pages into: {PATHS.cvat_shared_page_cls}")
    print(f"Staged pages into: {PATHS.cvat_shared_drawing_seg}")
    return len(rows)


def main() -> int:
    load_env()
    PATHS.ensure_all()

    n_files = _write_files_inventory()
    n_pages = _write_pages_inventory_and_share()
    print(f"Inventory complete: files={n_files}, pages={n_pages}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
