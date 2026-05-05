"""Promotion of training runs into ``model_registry/``.

Promotion is the *only* sanctioned path for weights to leave the experimental
zone (``runs/``) and become production-ready. Rules:

* Source MUST be inside ``runs/page_cls`` or ``runs/drawing_seg``.
* Destination MUST be inside ``model_registry/<model>/<version>``.
* ``current/`` is a versioned alias (real copy, not a symlink) updated last.
* Existing versions are NEVER overwritten unless ``force=True``.
* Every promoted version contains ``model_manifest.json`` with sha256 of weights.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .config import PATHS, ensure_under, read_yaml
from .training import export_run_metrics

VALID_MODELS = ("page_router", "drawing_segmenter")


@dataclass(frozen=True)
class PromotedModel:
    model_id: str
    version: str
    version_dir: Path
    current_dir: Path


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _release_cfg() -> dict:
    cfg = read_yaml(PATHS.configs / "model_release.yaml")
    if not cfg or "models" not in cfg:
        raise RuntimeError("configs/model_release.yaml missing or invalid")
    return cfg


def _model_cfg(model_id: str) -> dict:
    cfg = _release_cfg()
    if model_id not in cfg["models"]:
        raise ValueError(f"Unknown model_id {model_id!r}; expected one of {list(cfg['models'])}")
    return cfg["models"][model_id]


def _valid_run_zone(model_id: str) -> Path:
    return PATHS.runs_page_cls if model_id == "page_router" else PATHS.runs_drawing_seg


def _registry_dir(model_id: str) -> Path:
    return (
        PATHS.registry_page_router
        if model_id == "page_router"
        else PATHS.registry_drawing_segmenter
    )


def _version_dirname(model_id: str, version: str) -> str:
    if model_id == "page_router":
        return f"yolo11s_cls_page_router_{version}"
    return f"yolo11m_seg_drawing_{version}"


def _copy_artifacts(run_dir: Path, target_dir: Path, artifact_specs: list[dict]) -> dict[str, Path]:
    """Copy artifacts from ``run_dir`` into ``target_dir``. Returns ``dst_name -> path``."""
    copied: dict[str, Path] = {}
    for spec in artifact_specs:
        src = run_dir / spec["src"]
        dst = target_dir / spec["dst"]
        required = bool(spec.get("required", False))
        if not src.exists():
            if required:
                raise FileNotFoundError(f"Required artifact missing: {src}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied[spec["dst"]] = dst
    return copied


def _write_labels(target_dir: Path, labels_cfg: dict) -> tuple[Path, Path]:
    classes = labels_cfg.get("classes", [])
    names = [c["name"] for c in classes]

    txt = target_dir / "labels.txt"
    txt.write_text("\n".join(names) + "\n", encoding="utf-8")

    yml = target_dir / "labels.yaml"
    with yml.open("w", encoding="utf-8") as f:
        yaml.safe_dump(labels_cfg, f, sort_keys=False, allow_unicode=True)

    return txt, yml


def _write_metadata(
    target_dir: Path,
    *,
    model_id: str,
    version: str,
    metrics: dict[str, Any],
    base_model: str,
    weights_sha256: str,
) -> Path:
    out = target_dir / "metadata.yaml"
    payload = {
        "model_id": model_id,
        "version": version,
        "base_model": base_model,
        "weights_sha256": weights_sha256,
        "promoted_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "metrics_summary": {
            k: metrics[k]
            for k in (
                "metrics/accuracy_top1",
                "metrics/accuracy_top5",
                "metrics/mAP50(B)",
                "metrics/mAP50-95(B)",
                "metrics/mAP50(M)",
                "metrics/mAP50-95(M)",
            )
            if k in metrics
        },
    }
    with out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)
    return out


def _write_metrics_json(target_dir: Path, metrics: dict[str, Any]) -> Path:
    out = target_dir / "metrics.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)
    return out


def _write_dataset_ref(
    target_dir: Path,
    *,
    model_id: str,
    train_config: dict,
) -> Path:
    """Reference to the dataset used for training. Does NOT include the dataset itself."""
    out = target_dir / "dataset_ref.json"
    if model_id == "page_router":
        ref = {
            "task": "classification",
            "dataset_root": str(train_config.get("data", "data/datasets/page_cls")),
        }
    else:
        ref = {
            "task": "segmentation",
            "data_yaml": str(train_config.get("data", "data/datasets/drawing_seg_tiles/data.yaml")),
            "tile_size": train_config.get("tile_size"),
            "overlap": train_config.get("overlap"),
        }
    out.write_text(json.dumps(ref, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def _write_val_report_md(target_dir: Path, metrics: dict[str, Any], model_id: str, version: str) -> Path:
    out = target_dir / "val_report.md"
    lines = [f"# Validation report - {model_id} {version}", ""]
    if not metrics:
        lines.append("_No metrics recovered from run (results.csv missing)._")
    else:
        lines.append("| metric | value |")
        lines.append("|--------|-------|")
        for k in sorted(metrics):
            lines.append(f"| {k} | {metrics[k]} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _write_readme(target_dir: Path, *, model_id: str, version: str, base_model: str) -> Path:
    out = target_dir / "README.md"
    out.write_text(
        f"# {model_id} {version}\n\n"
        f"Base model: `{base_model}`. Promoted artifact for production use in `drawing2dxf`.\n\n"
        f"See `model_manifest.json`, `metrics.json` and `val_report.md` for details.\n",
        encoding="utf-8",
    )
    return out


def _write_manifest(
    target_dir: Path,
    *,
    model_cfg: dict,
    model_id: str,
    version: str,
    labels_cfg: dict,
    weights_pt: Path,
    weights_onnx: Path | None,
    metrics_file: Path,
    dataset_ref_file: Path,
    train_config: dict,
) -> Path:
    out = target_dir / "model_manifest.json"
    class_order = [c["name"] for c in labels_cfg.get("classes", [])]
    weights_sha = _sha256_file(weights_pt)

    manifest: dict[str, Any] = {
        "model_id": model_id,
        "version": version,
        "task": model_cfg["task"],
        "framework": model_cfg["framework"],
        "base_model": model_cfg["base_model"],
        "weights_pt": weights_pt.name,
        "weights_onnx": weights_onnx.name if weights_onnx else None,
        "class_order": class_order,
        "imgsz": train_config.get("imgsz"),
        "metrics_file": metrics_file.name,
        "dataset_ref": dataset_ref_file.name,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "sha256": {"weights_pt": weights_sha},
    }

    if model_id == "page_router":
        manifest["thresholds"] = labels_cfg.get(
            "thresholds",
            {"skip_specification_threshold": 0.95, "process_drawing_threshold": 0.70},
        )
    else:
        manifest["tile_size"] = train_config.get("tile_size", labels_cfg.get("tile_size"))
        manifest["overlap"] = train_config.get("overlap", labels_cfg.get("overlap"))
        manifest["data_yaml"] = "data.yaml"

    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def _refresh_current(version_dir: Path, current_dir: Path) -> None:
    if current_dir.exists():
        shutil.rmtree(current_dir)
    shutil.copytree(version_dir, current_dir)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def promote(model_id: str, run_dir: Path | str, version: str, *, force: bool = False) -> PromotedModel:
    """Copy a training run into ``model_registry/<model>/<version>`` + refresh current/."""
    if model_id not in VALID_MODELS:
        raise ValueError(f"Unknown model_id {model_id!r}; valid: {VALID_MODELS}")
    if not version.startswith("v"):
        raise ValueError(f"Version must start with 'v', got {version!r}")

    run_dir = Path(run_dir).resolve()
    ensure_under(run_dir, _valid_run_zone(model_id), label="run")

    model_cfg = _model_cfg(model_id)
    labels_cfg = read_yaml(model_cfg["labels_file"])
    train_cfg = read_yaml(model_cfg["train_config"])

    registry_root = _registry_dir(model_id)
    version_dir = registry_root / _version_dirname(model_id, version)
    current_dir = registry_root / "current"

    if version_dir.exists() and not force:
        raise FileExistsError(f"Registry version already exists: {version_dir}")
    if version_dir.exists() and force:
        shutil.rmtree(version_dir)
    version_dir.mkdir(parents=True, exist_ok=True)

    copied = _copy_artifacts(run_dir, version_dir, model_cfg["artifacts"])
    weights_pt = copied.get("best.pt")
    if not weights_pt or not weights_pt.exists():
        raise FileNotFoundError(f"best.pt was not copied from {run_dir}")
    weights_onnx = copied.get("best.onnx")

    if model_id == "drawing_segmenter":
        data_yaml_src = Path(train_cfg.get("data", ""))
        if data_yaml_src.exists():
            shutil.copy2(data_yaml_src, version_dir / "data.yaml")

    _write_labels(version_dir, labels_cfg)
    metrics = export_run_metrics(run_dir)
    metrics_file = _write_metrics_json(version_dir, metrics)
    dataset_ref_file = _write_dataset_ref(version_dir, model_id=model_id, train_config=train_cfg)
    _write_val_report_md(version_dir, metrics, model_id, version)
    _write_readme(version_dir, model_id=model_id, version=version, base_model=model_cfg["base_model"])
    _write_metadata(
        version_dir,
        model_id=model_id,
        version=version,
        metrics=metrics,
        base_model=model_cfg["base_model"],
        weights_sha256=_sha256_file(weights_pt),
    )

    used_cfg = version_dir / "train_config_used.yaml"
    with used_cfg.open("w", encoding="utf-8") as f:
        yaml.safe_dump(train_cfg, f, sort_keys=False, allow_unicode=True)

    _write_manifest(
        version_dir,
        model_cfg=model_cfg,
        model_id=model_id,
        version=version,
        labels_cfg=labels_cfg,
        weights_pt=weights_pt,
        weights_onnx=weights_onnx,
        metrics_file=metrics_file,
        dataset_ref_file=dataset_ref_file,
        train_config=train_cfg,
    )

    _refresh_current(version_dir, current_dir)

    return PromotedModel(
        model_id=model_id, version=version, version_dir=version_dir, current_dir=current_dir
    )
