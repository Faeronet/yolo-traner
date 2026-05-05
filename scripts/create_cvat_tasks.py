#!/usr/bin/env python3
"""(Optional) Create CVAT projects/tasks via REST API.

Reads ``configs/cvat.yaml`` and ``configs/labels_*.yaml`` and creates two
projects in CVAT:

* page_classification (annotation_type=tag, server-side files from cvat_shared)
* drawing_segmentation (annotation_type=polygon, server-side files from cvat_shared)

If automation is fragile in your CVAT version, follow the manual workflow in
``docs/annotation_guide.md`` instead.
"""

from __future__ import annotations

import sys

from yolo_train.config import PATHS, get_env, load_env, read_yaml
from yolo_train.cvat_client import CvatClient, CvatCredentials


def _labels_for_cvat(labels_cfg: dict, *, kind: str) -> list[dict]:
    out: list[dict] = []
    for c in labels_cfg.get("classes", []):
        out.append(
            {
                "name": c["name"],
                "attributes": [],
                "type": "tag" if kind == "tag" else "polygon",
            }
        )
    return out


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
        if not name:
            print(f"WARN: project {proj_key!r} has no name; skipping")
            continue
        labels_cfg = read_yaml(PATHS.root / proj["labels_file"])
        cvat_labels = _labels_for_cvat(labels_cfg, kind=proj.get("annotation_type", "tag"))
        project = client.ensure_project(name=name, labels=cvat_labels)
        print(f"Project ready: {name} (id={project.get('id')})")

    print("Done. Use CVAT UI to create tasks pointing to /home/django/share/<project_dir>.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
