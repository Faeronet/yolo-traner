#!/usr/bin/env python3
"""Install model_registry/<model>/current into a target project (drawing2dxf).

Copies:
  model_registry/page_router/current/      -> <target>/models/page_router/current/
  model_registry/drawing_segmenter/current -> <target>/models/drawing_segmenter/current/

And writes/updates:
  <target>/configs/models.yaml

Source is always model_registry/, never runs/ and never data/.
"""

from __future__ import annotations

import argparse
import sys

from yolo_train.config import get_env, load_env
from yolo_train.packaging import install_to_project


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        default=get_env("DRAWING2DXF_PROJECT", "../drawing2dxf"),
        help="Path to the consuming project (default: ../drawing2dxf)",
    )
    args = parser.parse_args()

    out = install_to_project(args.target)
    if not out:
        print("ERROR: nothing installed; promote a model first.", file=sys.stderr)
        return 2
    for k, v in out.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
