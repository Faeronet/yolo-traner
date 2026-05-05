#!/usr/bin/env python3
"""Train drawing_segmenter (YOLO11m-seg). Output is forced to runs/drawing_seg/."""

from __future__ import annotations

from pathlib import Path

from yolo_train.config import PATHS
from yolo_train.training import train_drawing_seg, write_train_config_used


def main() -> int:
    PATHS.ensure_all()
    cfg_path = PATHS.configs / "train_drawing_seg.yaml"
    outcome = train_drawing_seg(cfg_path)
    write_train_config_used(outcome.run_dir, cfg_path)
    print(f"Training finished. Run dir: {outcome.run_dir}")
    print("Run was saved ONLY under runs/drawing_seg/. Promote with:")
    rel = Path(outcome.run_dir).resolve().relative_to(PATHS.root)
    print(f"  make promote-drawing-seg RUN={rel} VERSION=v1.0.0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
