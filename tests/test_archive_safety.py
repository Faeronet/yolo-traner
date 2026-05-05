"""Verify that archive extraction refuses path traversal payloads."""

from __future__ import annotations

import io
import os
import tarfile
import zipfile
from pathlib import Path

import pytest

from yolo_train.archive import UnsafeArchiveError, extract_archive


def _make_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


def _make_tar(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, mode="w") as tf:
        for name, data in members.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))


def test_zip_traversal_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "evil.zip"
    _make_zip(archive, {"../escape.txt": b"x"})
    with pytest.raises(UnsafeArchiveError):
        extract_archive(archive, tmp_path / "out")


def test_zip_absolute_path_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "evil2.zip"
    abs_name = "/abs/path.txt" if os.name != "nt" else "C:/abs/path.txt"
    _make_zip(archive, {abs_name: b"x"})
    with pytest.raises(UnsafeArchiveError):
        extract_archive(archive, tmp_path / "out")


def test_tar_symlink_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "evil.tar"
    with tarfile.open(archive, mode="w") as tf:
        info = tarfile.TarInfo(name="link")
        info.type = tarfile.SYMTYPE
        info.linkname = "../etc/passwd"
        tf.addfile(info)
    with pytest.raises(UnsafeArchiveError):
        extract_archive(archive, tmp_path / "out")


def test_tar_size_limit_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "big.tar"
    _make_tar(archive, {"a.bin": b"\0" * 10})
    with pytest.raises(UnsafeArchiveError):
        extract_archive(archive, tmp_path / "out", max_total_bytes=1)


def test_zip_clean_extraction(tmp_path: Path) -> None:
    archive = tmp_path / "ok.zip"
    _make_zip(archive, {"a/b/c.txt": b"hello"})
    out = tmp_path / "out"
    extract_archive(archive, out)
    assert (out / "a" / "b" / "c.txt").read_bytes() == b"hello"
