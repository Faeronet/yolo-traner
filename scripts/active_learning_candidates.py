#!/usr/bin/env python3
"""Suggest pages for the next labeling round.

Strategy:

1. Run ``page_router`` on every page in ``data/pages/all`` (if a current
   model exists). Pick pages whose top-1 confidence is below a threshold -
   these are most informative to label next.
2. Fall back to "all unlabeled" pages if no model is available yet.

Outputs a CSV of candidate page paths in ``data/reports/active_learning.csv``.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from yolo_train.config import PATHS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=float, default=0.7, help="Top-1 confidence threshold")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    PATHS.ensure_all()

    pages = sorted(p for p in PATHS.pages_all.iterdir() if p.is_file() and p.suffix.lower() == ".png")
    if not pages:
        print("No pages in data/pages/all; nothing to suggest.")
        return 0

    weights = PATHS.registry_page_router / "current" / "best.pt"
    out_path = PATHS.reports / "active_learning.csv"

    rows: list[dict] = []
    if weights.exists():
        from ultralytics import YOLO

        model = YOLO(str(weights))
        results = model.predict(source=[str(p) for p in pages], imgsz=640, verbose=False, stream=True)
        for r in results:
            try:
                probs = r.probs
                top1 = float(probs.top1conf) if probs is not None else 0.0
                top1_name = r.names[int(probs.top1)] if probs is not None else "unknown"
            except Exception:  # noqa: BLE001
                continue
            if top1 < args.threshold:
                rows.append({"page": str(Path(r.path).resolve()), "top1": top1, "top1_class": top1_name})
    else:
        rows = [{"page": str(p), "top1": 0.0, "top1_class": "unknown"} for p in pages]

    rows = sorted(rows, key=lambda d: d["top1"])[: args.limit]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["page", "top1", "top1_class"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote {len(rows)} candidate(s) to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
