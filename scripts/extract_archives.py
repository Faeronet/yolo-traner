#!/usr/bin/env python3
"""Stage 1 of `make prepare`: copy/move archive into data/raw/archives and extract.

* Source archive may be passed as ``--archive ПДФ.rar`` (relative to project root)
  or as an absolute path. If it's not yet under ``data/raw/archives``, it is
  copied (not moved) so the original location remains intact.
* Extracts safely (no path traversal, no symlinks, capped total size).
* Sorts extracted files into:
    - data/raw/original_pdfs/    (*.pdf)
    - data/raw/original_images/  (*.png/jpg/tiff/bmp)
    - data/raw/extracted_files/  (everything else)
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from yolo_train.archive import extract_archive, is_archive
from yolo_train.config import PATHS
from yolo_train.image import ALL_IMAGE_SUFFIXES


def _stage_archive(src: Path) -> Path:
    PATHS.raw_archives.mkdir(parents=True, exist_ok=True)
    dst = PATHS.raw_archives / src.name
    if src.resolve() == dst.resolve():
        return dst
    if dst.exists() and dst.stat().st_size == src.stat().st_size:
        return dst
    shutil.copy2(src, dst)
    return dst


def _sort_extracted(extract_dir: Path) -> tuple[int, int, int]:
    n_pdf = n_img = n_other = 0
    PATHS.raw_pdfs.mkdir(parents=True, exist_ok=True)
    PATHS.raw_images.mkdir(parents=True, exist_ok=True)
    PATHS.raw_extracted.mkdir(parents=True, exist_ok=True)

    for src in extract_dir.rglob("*"):
        if not src.is_file():
            continue
        suffix = src.suffix.lower()
        if suffix == ".pdf":
            target = PATHS.raw_pdfs / src.name
            n_pdf += 1
        elif suffix in ALL_IMAGE_SUFFIXES:
            target = PATHS.raw_images / src.name
            n_img += 1
        else:
            rel = src.relative_to(extract_dir)
            target = PATHS.raw_extracted / rel
            n_other += 1
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.stat().st_size != src.stat().st_size:
            shutil.copy2(src, target)
    return n_pdf, n_img, n_other


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, help="Archive name or path (e.g. ПДФ.rar)")
    args = parser.parse_args()

    PATHS.ensure_all()

    candidate = Path(args.archive)
    if not candidate.is_absolute():
        # Try project root first, then data/raw/archives.
        c1 = PATHS.root / candidate
        c2 = PATHS.raw_archives / candidate
        candidate = c1 if c1.exists() else c2

    if not candidate.exists():
        print(f"ERROR: archive not found: {candidate}", file=sys.stderr)
        return 2
    if not is_archive(candidate):
        print(f"ERROR: not a supported archive: {candidate}", file=sys.stderr)
        return 2

    staged = _stage_archive(candidate)
    print(f"Archive staged at: {staged}")

    extract_dir = PATHS.raw_extracted / staged.stem
    extract_dir.mkdir(parents=True, exist_ok=True)
    extract_archive(staged, extract_dir)
    print(f"Extracted to: {extract_dir}")

    n_pdf, n_img, n_other = _sort_extracted(extract_dir)
    print(f"Sorted: {n_pdf} PDFs, {n_img} images, {n_other} other files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
