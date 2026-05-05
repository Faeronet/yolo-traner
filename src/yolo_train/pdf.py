"""PDF rasterization helpers.

Renders each page of a PDF into a PNG using PyMuPDF (``fitz``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import fitz  # PyMuPDF


def render_pdf_to_pngs(
    pdf_path: Path | str,
    out_dir: Path | str,
    *,
    dpi: int = 300,
    grayscale: bool = False,
    page_prefix: str | None = None,
) -> list[Path]:
    """Render every page of ``pdf_path`` into PNGs under ``out_dir``.

    Filenames look like ``<prefix>_p0001.png``. ``prefix`` defaults to the
    PDF stem.
    """
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    prefix = page_prefix or pdf_path.stem
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    cs = fitz.csGRAY if grayscale else fitz.csRGB

    written: list[Path] = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=matrix, colorspace=cs, alpha=False)
            target = out_dir / f"{prefix}_p{i:04d}.png"
            pix.save(target)
            written.append(target)
    return written


def render_many(
    pdf_paths: Iterable[Path | str],
    out_dir: Path | str,
    *,
    dpi: int = 300,
    grayscale: bool = False,
) -> list[Path]:
    """Render multiple PDFs into ``out_dir``."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pages: list[Path] = []
    for pdf in pdf_paths:
        pages.extend(render_pdf_to_pngs(pdf, out_dir, dpi=dpi, grayscale=grayscale))
    return pages
