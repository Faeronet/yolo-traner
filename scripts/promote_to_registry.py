#!/usr/bin/env python3
"""Promote a training run from runs/ into model_registry/.

Strict guarantees:
* RUN must be inside runs/page_cls or runs/drawing_seg.
* Destination is model_registry/<model>/<version_dirname> + current/.
* Existing version is never overwritten unless --force.
"""

from __future__ import annotations

import argparse
import sys

from yolo_train.registry import VALID_MODELS, promote


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=VALID_MODELS)
    parser.add_argument("--run", required=True, help="Path to a run directory under runs/<model>/")
    parser.add_argument("--version", required=True, help="Version, e.g. v1.0.0")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing version")
    args = parser.parse_args()

    try:
        result = promote(args.model, args.run, args.version, force=args.force)
    except (ValueError, FileNotFoundError, FileExistsError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Promoted {result.model_id} {result.version}:")
    print(f"  version dir: {result.version_dir}")
    print(f"  current dir: {result.current_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
