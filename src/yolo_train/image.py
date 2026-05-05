"""Image normalization, previews and thumbnails."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageOps

PNG_SUFFIXES = (".png",)
JPG_SUFFIXES = (".jpg", ".jpeg")
TIFF_SUFFIXES = (".tif", ".tiff")
BMP_SUFFIXES = (".bmp",)
ALL_IMAGE_SUFFIXES = PNG_SUFFIXES + JPG_SUFFIXES + TIFF_SUFFIXES + BMP_SUFFIXES


def is_image(path: Path | str) -> bool:
    return Path(path).suffix.lower() in ALL_IMAGE_SUFFIXES


def normalize_to_png(
    src: Path | str,
    dst: Path | str,
    *,
    max_long_edge: int | None = 4096,
) -> Path:
    """Re-save ``src`` as a PNG at ``dst`` (auto-rotates by EXIF, optional downscale)."""
    src = Path(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("L", "RGB"):
            im = im.convert("RGB")
        if max_long_edge:
            long_edge = max(im.size)
            if long_edge > max_long_edge:
                ratio = max_long_edge / long_edge
                new_size = (int(im.size[0] * ratio), int(im.size[1] * ratio))
                im = im.resize(new_size, Image.LANCZOS)
        im.save(dst, "PNG", optimize=True)
    return dst


def make_preview(src: Path | str, dst: Path | str, *, long_edge: int = 1600) -> Path:
    """Save a JPEG preview with bounded long edge."""
    src = Path(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((long_edge, long_edge), Image.LANCZOS)
        im.save(dst, "JPEG", quality=85, optimize=True)
    return dst


def make_thumbnail(src: Path | str, dst: Path | str, *, long_edge: int = 320) -> Path:
    """Save a tiny JPEG thumbnail."""
    return make_preview(src, dst, long_edge=long_edge)


def file_sha256(path: Path | str, *, chunk: int = 1 << 20) -> str:
    """Stream a file through SHA-256 and return the hex digest."""
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def image_size(path: Path | str) -> tuple[int, int]:
    """Return ``(width, height)`` without loading pixel data."""
    with Image.open(path) as im:
        return im.size
