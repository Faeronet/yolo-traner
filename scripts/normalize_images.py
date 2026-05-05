#!/usr/bin/env python3
"""Stage 3 of `make prepare`: ensure every page in data/pages/all is a clean PNG.

* Auto-rotates by EXIF.
* Caps long edge at ``SCAN_MAX_LONG_EDGE`` (default 4096).
* Re-saves non-PNG pages as PNG and removes the original.
"""

from __future__ import annotations

from pathlib import Path

from tqdm import tqdm

from yolo_train.config import PATHS, get_env, load_env
from yolo_train.image import normalize_to_png


def main() -> int:
    load_env()
    PATHS.ensure_all()

    max_long_edge = int(get_env("SCAN_MAX_LONG_EDGE", "4096") or "4096")
    pages = [p for p in PATHS.pages_all.iterdir() if p.is_file()]
    if not pages:
        print("No pages found under data/pages/all - nothing to normalize.")
        return 0

    print(f"Normalizing {len(pages)} page(s) (max long edge = {max_long_edge})")
    for page in tqdm(pages, desc="pages"):
        suffix = page.suffix.lower()
        if suffix == ".png":
            normalize_to_png(page, page, max_long_edge=max_long_edge)
            continue
        if suffix in (".jpg", ".jpeg", ".tif", ".tiff", ".bmp"):
            target = page.with_suffix(".png")
            normalize_to_png(page, target, max_long_edge=max_long_edge)
            if target.exists() and target != page:
                page.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
