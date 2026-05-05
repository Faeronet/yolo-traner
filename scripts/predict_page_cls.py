#!/usr/bin/env python3
"""Run page_router predictions on a directory of images.

Writes results into ``runs/predictions/page_cls/<run_name>/``. Always loads
weights from ``model_registry/page_router/current/best.pt``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from yolo_train.config import PATHS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(PATHS.pages_all), help="Image dir or file")
    parser.add_argument("--name", default="page_cls_pred")
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()

    weights = PATHS.registry_page_router / "current" / "best.pt"
    if not weights.exists():
        print(
            f"ERROR: weights not found: {weights}. Promote a run first.",
            file=sys.stderr,
        )
        return 2

    from ultralytics import YOLO

    out_root = PATHS.runs_predictions / "page_cls"
    out_root.mkdir(parents=True, exist_ok=True)

    model = YOLO(str(weights))
    results = model.predict(
        source=args.source,
        imgsz=args.imgsz,
        save=True,
        project=str(out_root),
        name=args.name,
        exist_ok=False,
    )
    print(f"Prediction run dir: {Path(results[0].save_dir) if results else out_root / args.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
