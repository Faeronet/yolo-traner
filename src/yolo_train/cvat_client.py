"""Thin wrapper around CVAT REST API.

This module is intentionally minimal: it only exposes the calls used by
``scripts/create_cvat_tasks.py`` and ``scripts/export_cvat_annotations.py``.
If automatic export is too brittle, the manual workflow described in
``docs/annotation_guide.md`` remains the supported fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests

from .config import get_env


@dataclass
class CvatCredentials:
    url: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "CvatCredentials":
        url = get_env("CVAT_API_URL", "http://localhost:8080/api") or ""
        user = get_env("CVAT_API_USER", "") or ""
        password = get_env("CVAT_API_PASSWORD", "") or ""
        if not url or not user or not password:
            raise RuntimeError(
                "CVAT credentials are missing. Set CVAT_API_URL/CVAT_API_USER/"
                "CVAT_API_PASSWORD in your .env file."
            )
        return cls(url=url.rstrip("/"), user=user, password=password)


class CvatClient:
    """Tiny REST client for CVAT (auth + projects + tasks + annotation export)."""

    def __init__(self, creds: CvatCredentials, *, verify: bool = True, timeout: float = 60.0):
        self._creds = creds
        self._session = requests.Session()
        self._session.verify = verify
        self._timeout = timeout
        self._auth()

    def _auth(self) -> None:
        r = self._session.post(
            f"{self._creds.url}/auth/login",
            json={"username": self._creds.user, "password": self._creds.password},
            timeout=self._timeout,
        )
        r.raise_for_status()
        token = r.json().get("key")
        if not token:
            raise RuntimeError("CVAT login did not return an auth token")
        self._session.headers.update({"Authorization": f"Token {token}"})

    # --- Projects ------------------------------------------------------------
    def find_project(self, name: str) -> dict | None:
        r = self._session.get(
            f"{self._creds.url}/projects",
            params={"search": name},
            timeout=self._timeout,
        )
        r.raise_for_status()
        for p in r.json().get("results", []):
            if p.get("name") == name:
                return p
        return None

    def create_project(self, name: str, labels: list[dict]) -> dict:
        r = self._session.post(
            f"{self._creds.url}/projects",
            json={"name": name, "labels": labels},
            timeout=self._timeout,
        )
        r.raise_for_status()
        return r.json()

    def ensure_project(self, name: str, labels: list[dict]) -> dict:
        existing = self.find_project(name)
        if existing is not None:
            return existing
        return self.create_project(name, labels)

    # --- Tasks ---------------------------------------------------------------
    def list_tasks(self, project_id: int) -> list[dict]:
        r = self._session.get(
            f"{self._creds.url}/tasks",
            params={"project_id": project_id, "page_size": 1000},
            timeout=self._timeout,
        )
        r.raise_for_status()
        return r.json().get("results", [])

    def create_task(self, *, project_id: int, name: str) -> dict:
        r = self._session.post(
            f"{self._creds.url}/tasks",
            json={"name": name, "project_id": project_id},
            timeout=self._timeout,
        )
        r.raise_for_status()
        return r.json()

    def attach_share_data(self, task_id: int, share_files: list[str]) -> None:
        """Attach files mounted at /home/django/share inside CVAT to a task."""
        r = self._session.post(
            f"{self._creds.url}/tasks/{task_id}/data",
            json={"server_files": share_files, "image_quality": 70},
            timeout=self._timeout,
        )
        r.raise_for_status()

    # --- Annotations export --------------------------------------------------
    def export_dataset(
        self,
        project_id: int,
        out_path: Path,
        *,
        export_format: str,
    ) -> Path:
        """Trigger and download a dataset export for the project.

        CVAT's actual API for this is asynchronous and version-dependent. This
        method is a placeholder that should be reviewed against the version
        of CVAT you actually deploy. If unreliable, fall back to the manual
        export described in ``docs/annotation_guide.md``.
        """
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        r = self._session.get(
            f"{self._creds.url}/projects/{project_id}/dataset",
            params={"format": export_format, "action": "download"},
            stream=True,
            timeout=self._timeout * 5,
        )
        r.raise_for_status()
        with out_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
        return out_path
