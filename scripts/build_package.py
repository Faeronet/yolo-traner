#!/usr/bin/env python3
"""Build production-ready model packages from model_registry/.

Produces:
  model_packages/page_router_yolo11s_cls_page_router_<VERSION>.tar.gz
  model_packages/drawing_segmenter_yolo11m_seg_drawing_<VERSION>.tar.gz
  model_packages/drawing2dxf_models_bundle_<VERSION>.tar.gz

No data/, runs/, exports, scans or images can leak into these archives:
they are built strictly from the package_whitelist of each model.
"""

from __future__ import annotations

import argparse
import sys

from yolo_train.packaging import build_bundle, build_model_package


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Version label, e.g. v1.0.0")
    args = parser.parse_args()

    parts = []
    for model_id in ("page_router", "drawing_segmenter"):
        try:
            built = build_model_package(model_id, args.version)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            print(f"WARN: cannot build {model_id} package: {exc}", file=sys.stderr)
            continue
        print(f"Built {model_id}: {built.archive_path}")
        parts.append(built)

    if not parts:
        print(
            "ERROR: nothing was packaged. Promote at least one model first "
            "with `make promote-page-cls` or `make promote-drawing-seg`.",
            file=sys.stderr,
        )
        return 2

    bundle = build_bundle(args.version, parts)
    print(f"Bundle: {bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
