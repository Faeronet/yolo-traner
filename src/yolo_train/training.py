"""Training entry points used by ``scripts/train_*.py``.

Strict rule: training results MUST land under ``runs/page_cls`` or
``runs/drawing_seg``. The functions below enforce this with
``ensure_under(...)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .config import PATHS, ensure_under, read_yaml


@dataclass(frozen=True)
class TrainOutcome:
    run_dir: Path
    metrics: dict[str, Any]


def _load_train_kwargs(config_path: Path | str) -> dict:
    cfg = read_yaml(config_path)
    if not cfg:
        raise FileNotFoundError(f"Training config not found or empty: {config_path}")
    return dict(cfg)


def _split_kwargs(cfg: dict) -> tuple[str, dict]:
    """Pop ``model`` from cfg and return ``(model, kwargs_for_yolo.train)``."""
    model = cfg.pop("model", None)
    if not model:
        raise ValueError("Training config is missing 'model' field")

    cfg.pop("tile_size", None)
    cfg.pop("overlap", None)
    return model, cfg


def train_page_cls(config_path: Path | str = "configs/train_page_cls.yaml") -> TrainOutcome:
    """Train YOLO11s-cls. Output is forced under ``runs/page_cls``."""
    from ultralytics import YOLO

    cfg = _load_train_kwargs(config_path)
    model_name, kwargs = _split_kwargs(cfg)

    project = Path(kwargs.get("project", PATHS.runs_page_cls))
    ensure_under(project, PATHS.runs_page_cls, label="page_cls training project")
    kwargs["project"] = str(project)

    model = YOLO(model_name)
    results = model.train(**kwargs)
    return TrainOutcome(run_dir=Path(results.save_dir), metrics=getattr(results, "results_dict", {}) or {})


def train_drawing_seg(config_path: Path | str = "configs/train_drawing_seg.yaml") -> TrainOutcome:
    """Train YOLO11m-seg. Output is forced under ``runs/drawing_seg``."""
    from ultralytics import YOLO

    cfg = _load_train_kwargs(config_path)
    model_name, kwargs = _split_kwargs(cfg)

    project = Path(kwargs.get("project", PATHS.runs_drawing_seg))
    ensure_under(project, PATHS.runs_drawing_seg, label="drawing_seg training project")
    kwargs["project"] = str(project)

    model = YOLO(model_name)
    results = model.train(**kwargs)
    return TrainOutcome(run_dir=Path(results.save_dir), metrics=getattr(results, "results_dict", {}) or {})


def export_run_metrics(run_dir: Path | str) -> dict[str, Any]:
    """Best-effort scan of an Ultralytics run dir for results.csv -> dict."""
    run_dir = Path(run_dir)
    results_csv = run_dir / "results.csv"
    if not results_csv.exists():
        return {}
    import csv

    with results_csv.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {}
    last = rows[-1]
    out: dict[str, Any] = {}
    for k, v in last.items():
        try:
            out[k.strip()] = float(v)
        except (TypeError, ValueError):
            out[k.strip()] = v
    return out


def write_train_config_used(run_dir: Path | str, config_path: Path | str) -> Path:
    """Copy the training config into the run dir as ``train_config_used.yaml``."""
    run_dir = Path(run_dir)
    cfg = read_yaml(config_path)
    out = run_dir / "train_config_used.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)
    return out
