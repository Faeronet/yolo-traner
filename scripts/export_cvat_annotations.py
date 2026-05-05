#!/usr/bin/env python3
"""(Optional) Pull annotations from CVAT into ``data/cvat_exports``.

This is best-effort: CVAT's export API is asynchronous and version-dependent.
If this script fails for your CVAT version, use the manual workflow in
``docs/annotation_guide.md``: download exports from the UI and unzip into
``data/cvat_exports/page_classification`` and
``data/cvat_exports/drawing_segmentation``.
"""

from __future__ import annotations

import sys

from yolo_train.config import PATHS, get_env, load_env, read_yaml
from yolo_train.cvat_client import CvatClient, CvatCredentials


def main() -> int:
    load_env()
    cvat_cfg = read_yaml(PATHS.configs / "cvat.yaml")
    if not cvat_cfg:
        print("ERROR: configs/cvat.yaml is missing", file=sys.stderr)
        return 2

    try:
        creds = CvatCredentials.from_env()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    client = CvatClient(creds, verify=cvat_cfg.get("api", {}).get("ssl_verify", True))

    for proj_key, proj in cvat_cfg.get("projects", {}).items():
        env_name = proj.get("name_env")
        name = (get_env(env_name) if env_name else None) or proj.get("default_name")
        export_format = proj.get("export_format", "CVAT for images 1.1")
        export_dir = PATHS.root / proj["export_dir"]
        export_dir.mkdir(parents=True, exist_ok=True)

        project = client.find_project(name=name)
        if not project:
            print(f"WARN: project {name!r} not found; skipping {proj_key}")
            continue

        out_zip = export_dir / f"{name}.zip"
        try:
            client.export_dataset(project["id"], out_zip, export_format=export_format)
            print(f"Exported {name} -> {out_zip}")
        except Exception as exc:  # noqa: BLE001
            print(
                f"WARN: failed to export {name!r} via API ({exc}). "
                f"Use the manual export described in docs/annotation_guide.md.",
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
