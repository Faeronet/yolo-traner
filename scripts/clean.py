#!/usr/bin/env python3
"""Remove caches and temporary files.

Does NOT touch ``data/``, ``runs/``, ``model_registry/`` or ``model_packages/``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from yolo_train.config import PATHS

CACHE_DIR_NAMES = (
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".ipynb_checkpoints",
)
CACHE_FILE_SUFFIXES = (".pyc", ".pyo")


def main() -> int:
    removed_dirs = removed_files = 0
    for path in PATHS.root.rglob("*"):
        try:
            rel = path.relative_to(PATHS.root)
        except ValueError:
            continue
        # Never enter protected zones.
        if rel.parts and rel.parts[0] in {"data", "runs", "model_registry", "model_packages"}:
            continue
        if path.is_dir() and path.name in CACHE_DIR_NAMES:
            shutil.rmtree(path, ignore_errors=True)
            removed_dirs += 1
        elif path.is_file() and path.suffix in CACHE_FILE_SUFFIXES:
            path.unlink(missing_ok=True)
            removed_files += 1
    print(f"Removed {removed_dirs} cache dir(s) and {removed_files} cache file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
