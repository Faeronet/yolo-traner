"""Safe archive extraction (RAR / ZIP / 7z / TAR).

Defends against path traversal (``../`` payloads), absolute paths, symlinks
pointing outside the destination, and zip-bombs (size cap).
"""

from __future__ import annotations

import os
import shutil
import tarfile
import zipfile
from pathlib import Path
from typing import Iterable

import py7zr
import rarfile

# Soft cap on total uncompressed bytes (prevents zip-bombs). Override per-call.
DEFAULT_MAX_TOTAL_BYTES = 200 * 1024**3  # 200 GiB


class UnsafeArchiveError(RuntimeError):
    """Raised when an archive entry violates safety checks."""


def _is_within(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    try:
        child_r.relative_to(parent_r)
        return True
    except ValueError:
        return False


def _check_member_name(name: str, dest: Path) -> Path:
    """Resolve a member name relative to ``dest`` and verify it stays inside."""
    if not name or name in (".", ".."):
        raise UnsafeArchiveError(f"Invalid archive member name: {name!r}")
    member_path = (dest / name).resolve()
    if os.path.isabs(name):
        raise UnsafeArchiveError(f"Absolute path in archive: {name!r}")
    if not _is_within(member_path, dest):
        raise UnsafeArchiveError(f"Archive member escapes destination: {name!r}")
    return member_path


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def extract_archive(
    archive: Path | str,
    dest: Path | str,
    *,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
) -> Path:
    """Extract ``archive`` into ``dest`` safely.

    Returns ``dest`` as a resolved ``Path``. The destination is created if
    missing. The kind of archive is detected by extension.
    """
    archive = Path(archive)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)

    suffix = "".join(archive.suffixes).lower()
    name = archive.name.lower()

    if name.endswith(".rar"):
        _extract_rar(archive, dest, max_total_bytes=max_total_bytes)
    elif name.endswith(".zip"):
        _extract_zip(archive, dest, max_total_bytes=max_total_bytes)
    elif name.endswith(".7z"):
        _extract_7z(archive, dest, max_total_bytes=max_total_bytes)
    elif suffix.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
        _extract_tar(archive, dest, max_total_bytes=max_total_bytes)
    else:
        raise UnsafeArchiveError(f"Unsupported archive type: {archive.name}")

    return dest.resolve()


def is_archive(path: Path | str) -> bool:
    """Return True if ``path`` looks like a supported archive."""
    name = Path(path).name.lower()
    if name.endswith((".rar", ".zip", ".7z")):
        return True
    return any(name.endswith(s) for s in (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz"))


def iter_files(root: Path | str, *, suffixes: Iterable[str] | None = None) -> Iterable[Path]:
    """Yield files under ``root`` (optionally filtered by suffix, case-insensitive)."""
    root = Path(root)
    norm = {s.lower() for s in suffixes} if suffixes else None
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if norm is not None and p.suffix.lower() not in norm:
            continue
        yield p


# -----------------------------------------------------------------------------
# Backend implementations
# -----------------------------------------------------------------------------
def _extract_rar(archive: Path, dest: Path, *, max_total_bytes: int) -> None:
    with rarfile.RarFile(archive) as rf:
        total = 0
        for info in rf.infolist():
            if info.isdir():
                continue
            target = _check_member_name(info.filename, dest)
            total += int(getattr(info, "file_size", 0) or 0)
            if total > max_total_bytes:
                raise UnsafeArchiveError(
                    f"Archive {archive.name} exceeds max_total_bytes={max_total_bytes}"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            with rf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def _extract_zip(archive: Path, dest: Path, *, max_total_bytes: int) -> None:
    with zipfile.ZipFile(archive) as zf:
        total = 0
        for info in zf.infolist():
            if info.is_dir():
                continue
            target = _check_member_name(info.filename, dest)
            total += int(info.file_size or 0)
            if total > max_total_bytes:
                raise UnsafeArchiveError(
                    f"Archive {archive.name} exceeds max_total_bytes={max_total_bytes}"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info, "r") as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def _extract_7z(archive: Path, dest: Path, *, max_total_bytes: int) -> None:
    with py7zr.SevenZipFile(archive, mode="r") as z:
        names = z.getnames()
        for name in names:
            _check_member_name(name, dest)
        z.extractall(path=dest)
    total = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
    if total > max_total_bytes:
        raise UnsafeArchiveError(
            f"Archive {archive.name} exceeds max_total_bytes={max_total_bytes}"
        )


def _extract_tar(archive: Path, dest: Path, *, max_total_bytes: int) -> None:
    with tarfile.open(archive, mode="r:*") as tf:
        total = 0
        for member in tf.getmembers():
            if member.isdir():
                continue
            if member.issym() or member.islnk():
                raise UnsafeArchiveError(
                    f"Symlinks/hardlinks are not allowed in archive: {member.name!r}"
                )
            _check_member_name(member.name, dest)
            total += int(member.size or 0)
            if total > max_total_bytes:
                raise UnsafeArchiveError(
                    f"Archive {archive.name} exceeds max_total_bytes={max_total_bytes}"
                )
        tf.extractall(dest)
