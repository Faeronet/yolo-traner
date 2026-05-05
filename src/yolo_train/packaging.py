"""Build production packages from ``model_registry/``.

Hard guarantees enforced here:

* Source MUST be inside ``model_registry/<model>/current``.
* Only files in ``package_whitelist`` end up in the archive.
* Anything matching ``package_blacklist_patterns`` is rejected (defence in depth).
* Result lives under ``model_packages/`` and contains no datasets, no exports,
  no scans, no tiles, no train images, no logs, no run metadata.
"""

from __future__ import annotations

import fnmatch
import tarfile
from dataclasses import dataclass
from pathlib import Path

from .config import PATHS, ensure_under, read_yaml


@dataclass(frozen=True)
class BuiltPackage:
    model_id: str
    version: str
    archive_path: Path


def _release_cfg() -> dict:
    cfg = read_yaml(PATHS.configs / "model_release.yaml")
    if not cfg or "models" not in cfg:
        raise RuntimeError("configs/model_release.yaml is missing")
    return cfg


def _violates_blacklist(rel_path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, pat) for pat in patterns)


def _archive_name(model_id: str, version: str) -> str:
    if model_id == "page_router":
        return f"page_router_yolo11s_cls_page_router_{version}.tar.gz"
    return f"drawing_segmenter_yolo11m_seg_drawing_{version}.tar.gz"


def _registry_current(model_id: str) -> Path:
    if model_id == "page_router":
        return PATHS.registry_page_router / "current"
    if model_id == "drawing_segmenter":
        return PATHS.registry_drawing_segmenter / "current"
    raise ValueError(f"Unknown model_id {model_id!r}")


def build_model_package(model_id: str, version: str) -> BuiltPackage:
    """Build a single model's tar.gz package."""
    cfg = _release_cfg()
    if model_id not in cfg["models"]:
        raise ValueError(f"Unknown model_id {model_id!r}")
    model_cfg = cfg["models"][model_id]
    whitelist = list(model_cfg.get("package_whitelist", []))
    blacklist = list(cfg.get("package_blacklist_patterns", []))

    src = _registry_current(model_id).resolve()
    if not src.exists():
        raise FileNotFoundError(f"model_registry/{model_id}/current is missing: {src}")
    ensure_under(src, PATHS.model_registry, label="package source")

    PATHS.model_packages.mkdir(parents=True, exist_ok=True)
    archive_path = PATHS.model_packages / _archive_name(model_id, version)

    with tarfile.open(archive_path, mode="w:gz") as tar:
        for name in whitelist:
            f = src / name
            if not f.exists():
                continue
            rel = f"{model_id}/{name}"
            if _violates_blacklist(rel, blacklist):
                raise RuntimeError(
                    f"File {rel} matches package_blacklist_patterns - refusing to package."
                )
            tar.add(f, arcname=rel)

    return BuiltPackage(model_id=model_id, version=version, archive_path=archive_path)


def build_bundle(version: str, parts: list[BuiltPackage]) -> Path:
    """Build a combined bundle archive that contains both per-model archives."""
    PATHS.model_packages.mkdir(parents=True, exist_ok=True)
    bundle = PATHS.model_packages / f"drawing2dxf_models_bundle_{version}.tar.gz"
    with tarfile.open(bundle, mode="w:gz") as tar:
        for p in parts:
            tar.add(p.archive_path, arcname=p.archive_path.name)
    return bundle


def install_to_project(target_root: Path | str) -> dict[str, Path]:
    """Copy ``model_registry/<model>/current`` into a target project.

    Layout produced inside ``target_root``::

        models/page_router/current/...
        models/drawing_segmenter/current/...
        configs/models.yaml
    """
    import shutil

    import yaml as _yaml

    target_root = Path(target_root).resolve()
    target_root.mkdir(parents=True, exist_ok=True)

    out: dict[str, Path] = {}
    for model_id in ("page_router", "drawing_segmenter"):
        src = _registry_current(model_id)
        if not src.exists():
            continue
        dst = target_root / "models" / model_id / "current"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        out[model_id] = dst

    cfg_dir = target_root / "configs"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    models_yaml = cfg_dir / "models.yaml"
    payload = {
        "page_router": {
            "weights_pt": "models/page_router/current/best.pt",
            "weights_onnx": "models/page_router/current/best.onnx",
            "manifest": "models/page_router/current/model_manifest.json",
        },
        "drawing_segmenter": {
            "weights_pt": "models/drawing_segmenter/current/best.pt",
            "weights_onnx": "models/drawing_segmenter/current/best.onnx",
            "manifest": "models/drawing_segmenter/current/model_manifest.json",
        },
    }
    with models_yaml.open("w", encoding="utf-8") as f:
        _yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)
    out["models_yaml"] = models_yaml
    return out
