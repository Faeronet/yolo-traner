#!/usr/bin/env python3
"""Train page_router (YOLO11s-cls). Output is forced to runs/page_cls/."""

from __future__ import annotations

from pathlib import Path

from yolo_train.config import PATHS
from yolo_train.training import train_page_cls, write_train_config_used


def main() -> int:
    PATHS.ensure_all()
    cfg_path = PATHS.configs / "train_page_cls.yaml"
    outcome = train_page_cls(cfg_path)
    write_train_config_used(outcome.run_dir, cfg_path)
    print(f"Training finished. Run dir: {outcome.run_dir}")
    print("Run was saved ONLY under runs/page_cls/. Promote with:")
    rel = Path(outcome.run_dir).resolve().relative_to(PATHS.root)
    print(f"  make promote-page-cls RUN={rel} VERSION=v1.0.0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
