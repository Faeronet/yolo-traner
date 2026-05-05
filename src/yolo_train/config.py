"""Project paths, environment loading and small config helpers.

The ``Paths`` dataclass is the single source of truth for every directory in
the project. Scripts must use it instead of hard-coding paths.

Strict zone separation is encoded here: each zone has its own attribute and
the helpers refuse to mix them (e.g. ``ensure_under(path, Paths.runs)``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv


def _project_root() -> Path:
    """Return the project root (directory that contains ``pyproject.toml``)."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


PROJECT_ROOT: Path = _project_root()


@lru_cache(maxsize=1)
def load_env() -> None:
    """Load ``.env`` from project root if present (idempotent)."""
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)


@dataclass(frozen=True)
class Paths:
    """All canonical project paths. Never instantiate twice; use ``PATHS``."""

    root: Path = PROJECT_ROOT

    # --- Top-level zones (do NOT mix) ----------------------------------------
    data: Path = field(default_factory=lambda: PROJECT_ROOT / "data")
    runs: Path = field(default_factory=lambda: PROJECT_ROOT / "runs")
    model_registry: Path = field(default_factory=lambda: PROJECT_ROOT / "model_registry")
    model_packages: Path = field(default_factory=lambda: PROJECT_ROOT / "model_packages")

    configs: Path = field(default_factory=lambda: PROJECT_ROOT / "configs")
    scripts: Path = field(default_factory=lambda: PROJECT_ROOT / "scripts")
    docs: Path = field(default_factory=lambda: PROJECT_ROOT / "docs")
    infra: Path = field(default_factory=lambda: PROJECT_ROOT / "infra")
    tests: Path = field(default_factory=lambda: PROJECT_ROOT / "tests")

    # --- data/ subdirectories ------------------------------------------------
    raw_archives: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "raw" / "archives")
    raw_extracted: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "raw" / "extracted_files"
    )
    raw_images: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "raw" / "original_images"
    )
    raw_pdfs: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "raw" / "original_pdfs")
    scans: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "scans")

    pages_all: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "pages" / "all")
    pages_previews: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "pages" / "previews"
    )
    pages_thumbnails: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "pages" / "thumbnails"
    )

    cvat_shared: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "cvat_shared")
    cvat_shared_page_cls: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "cvat_shared" / "page_classification"
    )
    cvat_shared_drawing_seg: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "cvat_shared" / "drawing_segmentation"
    )

    cvat_exports: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "cvat_exports")
    cvat_export_page_cls: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "cvat_exports" / "page_classification"
    )
    cvat_export_drawing_seg: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "cvat_exports" / "drawing_segmentation"
    )

    datasets: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "datasets")
    dataset_page_cls: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "datasets" / "page_cls"
    )
    dataset_drawing_seg: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "datasets" / "drawing_seg"
    )
    dataset_drawing_seg_tiles: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "datasets" / "drawing_seg_tiles"
    )

    splits: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "splits")
    tiles: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "tiles")
    inventory: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "inventory")
    reports: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "reports")

    # --- runs/ subdirectories ------------------------------------------------
    runs_page_cls: Path = field(default_factory=lambda: PROJECT_ROOT / "runs" / "page_cls")
    runs_drawing_seg: Path = field(default_factory=lambda: PROJECT_ROOT / "runs" / "drawing_seg")
    runs_predictions: Path = field(default_factory=lambda: PROJECT_ROOT / "runs" / "predictions")

    # --- model_registry/ subdirectories --------------------------------------
    registry_page_router: Path = field(
        default_factory=lambda: PROJECT_ROOT / "model_registry" / "page_router"
    )
    registry_drawing_segmenter: Path = field(
        default_factory=lambda: PROJECT_ROOT / "model_registry" / "drawing_segmenter"
    )

    def ensure_all(self) -> None:
        """Create every project directory (idempotent)."""
        for value in self.__dict__.values():
            if isinstance(value, Path):
                value.mkdir(parents=True, exist_ok=True)


PATHS = Paths()


# -----------------------------------------------------------------------------
# Zone safety helpers
# -----------------------------------------------------------------------------
def is_within(child: Path, parent: Path) -> bool:
    """Return True iff ``child`` is inside ``parent`` (after resolution)."""
    child = Path(child).resolve()
    parent = Path(parent).resolve()
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def ensure_under(path: Path, zone: Path, *, label: str = "path") -> Path:
    """Raise ``ValueError`` if ``path`` is not located under ``zone``."""
    p = Path(path).resolve()
    if not is_within(p, zone):
        raise ValueError(f"{label} {p} must be located under {zone}")
    return p


# -----------------------------------------------------------------------------
# YAML helpers
# -----------------------------------------------------------------------------
def read_yaml(path: Path | str) -> dict:
    """Read a YAML file into a dict (returns ``{}`` if missing)."""
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_yaml(path: Path | str, data: dict) -> None:
    """Write a dict to a YAML file (creates parent dirs)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


# -----------------------------------------------------------------------------
# Env helpers
# -----------------------------------------------------------------------------
def get_env(name: str, default: str | None = None) -> str | None:
    """Return env variable, loading ``.env`` lazily."""
    load_env()
    return os.environ.get(name, default)
