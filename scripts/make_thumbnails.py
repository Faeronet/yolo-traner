#!/usr/bin/env python3
"""Stage 5 of `make prepare`: build previews and thumbnails for every page."""

from __future__ import annotations

from tqdm import tqdm

from yolo_train.config import PATHS
from yolo_train.image import make_preview, make_thumbnail


def main() -> int:
    PATHS.ensure_all()
    pages = sorted(p for p in PATHS.pages_all.iterdir() if p.is_file() and p.suffix.lower() == ".png")
    if not pages:
        print("No pages found - nothing to do.")
        return 0

    for p in tqdm(pages, desc="previews"):
        target = PATHS.pages_previews / (p.stem + ".jpg")
        if not target.exists():
            make_preview(p, target, long_edge=1600)
    for p in tqdm(pages, desc="thumbs"):
        target = PATHS.pages_thumbnails / (p.stem + ".jpg")
        if not target.exists():
            make_thumbnail(p, target, long_edge=320)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
