"""Image + YOLO segmentation polygon tiling.

Splits an image and its YOLO-seg labels into overlapping square tiles. Each
tile keeps every polygon clipped to its bounds. Empty tiles are skipped.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
from PIL import Image

from .yolo_formats import parse_yolo_seg_label, write_yolo_seg_label


@dataclass(frozen=True)
class Tile:
    image_path: Path
    label_path: Path


def _polygon_in_tile(
    coords_norm: Sequence[float],
    img_w: int,
    img_h: int,
    tile_x: int,
    tile_y: int,
    tile_w: int,
    tile_h: int,
) -> list[float] | None:
    """Clip a normalized polygon (full-image coords) into tile coords.

    Returns the polygon in tile-normalized coordinates, or ``None`` if the
    intersection with the tile is empty / degenerate.
    """
    if len(coords_norm) < 6:
        return None

    pts = np.array(coords_norm, dtype=np.float32).reshape(-1, 2)
    pts[:, 0] *= img_w
    pts[:, 1] *= img_h

    poly = pts.astype(np.float32)
    rect = np.array(
        [
            [tile_x, tile_y],
            [tile_x + tile_w, tile_y],
            [tile_x + tile_w, tile_y + tile_h],
            [tile_x, tile_y + tile_h],
        ],
        dtype=np.float32,
    )

    inter, _ = cv2.intersectConvexConvex(poly, rect, handleNested=True)
    if inter is None or len(inter) < 3:
        return None
    inter = inter.reshape(-1, 2)
    inter[:, 0] = (inter[:, 0] - tile_x) / tile_w
    inter[:, 1] = (inter[:, 1] - tile_y) / tile_h
    inter = np.clip(inter, 0.0, 1.0)
    flat = inter.flatten().tolist()
    return flat if len(flat) >= 6 else None


def tile_image_and_labels(
    image_path: Path | str,
    label_path: Path | str,
    out_images_dir: Path | str,
    out_labels_dir: Path | str,
    *,
    tile_size: int = 1024,
    overlap: int = 128,
    min_polygons_per_tile: int = 1,
) -> list[Tile]:
    """Tile a single image+label pair, returning the list of created tiles."""
    image_path = Path(image_path)
    label_path = Path(label_path)
    out_images_dir = Path(out_images_dir)
    out_labels_dir = Path(out_labels_dir)
    out_images_dir.mkdir(parents=True, exist_ok=True)
    out_labels_dir.mkdir(parents=True, exist_ok=True)

    polygons = parse_yolo_seg_label(label_path)

    with Image.open(image_path) as im:
        im = im.convert("RGB")
        w, h = im.size
        arr = np.array(im)

    stride = max(1, tile_size - overlap)
    written: list[Tile] = []
    tile_idx = 0

    ys = list(range(0, max(1, h - tile_size + 1), stride)) or [0]
    xs = list(range(0, max(1, w - tile_size + 1), stride)) or [0]
    if ys[-1] + tile_size < h:
        ys.append(h - tile_size)
    if xs[-1] + tile_size < w:
        xs.append(w - tile_size)

    for y in ys:
        for x in xs:
            tile_w = min(tile_size, w - x)
            tile_h = min(tile_size, h - y)
            tile_polygons: list[tuple[int, list[float]]] = []
            for cls, coords in polygons:
                clipped = _polygon_in_tile(coords, w, h, x, y, tile_w, tile_h)
                if clipped is not None:
                    tile_polygons.append((cls, clipped))
            if len(tile_polygons) < min_polygons_per_tile:
                continue

            tile_arr = arr[y : y + tile_h, x : x + tile_w]
            tile_idx += 1
            stem = f"{image_path.stem}_t{tile_idx:04d}"
            tile_img_path = out_images_dir / f"{stem}.png"
            tile_label_path = out_labels_dir / f"{stem}.txt"
            Image.fromarray(tile_arr).save(tile_img_path, "PNG")
            write_yolo_seg_label(tile_label_path, tile_polygons)
            written.append(Tile(image_path=tile_img_path, label_path=tile_label_path))

    return written
