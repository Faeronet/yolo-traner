#!/usr/bin/env python3
"""Stage 2 of `make prepare`: render every PDF in data/raw/original_pdfs to PNG pages.

Pages are written to ``data/pages/all/<pdf_stem>_p<NNNN>.png`` at DPI controlled
by ``PDF_RENDER_DPI`` (default 300).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from tqdm import tqdm

from yolo_train.config import PATHS, get_env, load_env
from yolo_train.pdf import render_pdf_to_pngs


def main() -> int:
    load_env()
    PATHS.ensure_all()

    dpi = int(get_env("PDF_RENDER_DPI", "300") or "300")

    pdfs = sorted(PATHS.raw_pdfs.rglob("*.pdf"))
    if not pdfs:
        print("No PDFs found under data/raw/original_pdfs - nothing to render.")
        return 0

    print(f"Rendering {len(pdfs)} PDF(s) at {dpi} DPI -> {PATHS.pages_all}")
    total_pages = 0
    for pdf in tqdm(pdfs, desc="PDFs"):
        try:
            written = render_pdf_to_pngs(pdf, PATHS.pages_all, dpi=dpi)
            total_pages += len(written)
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: failed to render {pdf}: {exc}", file=sys.stderr)
    print(f"Rendered {total_pages} page(s).")

    # Also include any standalone images (treated as single-page documents).
    n_imgs = 0
    for img in PATHS.raw_images.rglob("*"):
        if not img.is_file():
            continue
        if img.suffix.lower() not in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"):
            continue
        target = PATHS.pages_all / f"{img.stem}_p0001{img.suffix.lower()}"
        if target.exists():
            continue
        target.write_bytes(img.read_bytes())
        n_imgs += 1
    if n_imgs:
        print(f"Imported {n_imgs} standalone image(s) as single-page documents.")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    raise SystemExit(main())
