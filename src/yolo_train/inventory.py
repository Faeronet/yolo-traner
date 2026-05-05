"""Inventory CSV writers/readers.

Files produced under ``data/inventory/``:

* ``files_inventory.csv``      - every source file (archive, pdf, image)
* ``pages_inventory.csv``      - every rendered page PNG
* ``page_labels.csv``          - one row per page, label assigned via CVAT
* ``split_manifest.csv``       - which page belongs to which split
* ``duplicates_report.csv``    - perceptual / hash duplicates
* ``source_licenses.csv``      - licensing info per source
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Sequence

FILES_FIELDS = ("file_id", "rel_path", "kind", "size_bytes", "sha256", "source")
PAGES_FIELDS = (
    "page_id",
    "source_file_id",
    "source_rel_path",
    "page_index",
    "width",
    "height",
    "rel_path",
    "sha256",
)
PAGE_LABELS_FIELDS = ("page_id", "label", "source_task", "annotator", "annotated_at")
SPLIT_FIELDS = ("page_id", "split")
DUPLICATES_FIELDS = ("page_id_a", "page_id_b", "score", "method")
LICENSES_FIELDS = ("source", "license", "owner", "notes")


def write_csv(path: Path | str, fieldnames: Sequence[str], rows: Iterable[dict]) -> Path:
    """Write ``rows`` to ``path`` as UTF-8 CSV (creates parent dirs)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    return p


def read_csv(path: Path | str) -> list[dict]:
    """Read a CSV into a list of dicts (returns ``[]`` if missing)."""
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
