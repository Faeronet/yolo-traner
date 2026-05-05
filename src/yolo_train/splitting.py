"""Train / val / test splitting with leakage protection.

The split key is the *source document* (e.g. PDF stem), so every page
of the same drawing always lands in the same split.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Iterable, Mapping


def stable_hash(key: str) -> int:
    """Deterministic 64-bit hash (independent of Python's PYTHONHASHSEED)."""
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def assign_split(
    key: str,
    *,
    train: float = 0.8,
    val: float = 0.1,
    test: float = 0.1,
    salt: str = "",
) -> str:
    """Return ``"train"``, ``"val"`` or ``"test"`` for a stable key."""
    total = train + val + test
    if total <= 0:
        raise ValueError("Split fractions must sum to a positive value")
    train_n, val_n = train / total, val / total
    bucket = (stable_hash(salt + ":" + key) % 10_000) / 10_000.0
    if bucket < train_n:
        return "train"
    if bucket < train_n + val_n:
        return "val"
    return "test"


def split_by_group(
    items: Iterable[Mapping[str, str]],
    *,
    group_key: str,
    train: float = 0.8,
    val: float = 0.1,
    test: float = 0.1,
    salt: str = "",
) -> dict[str, list[dict]]:
    """Split items so every group goes entirely into a single split.

    ``items`` is an iterable of mappings; ``group_key`` is the column name
    used as the grouping key. Returns ``{"train": [...], "val": [...], "test": [...]}``.
    """
    items = list(items)
    by_group: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        g = str(it.get(group_key, "")) or stable_hash(repr(it)).__str__()
        by_group[g].append(dict(it))

    out: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    for group, members in by_group.items():
        split = assign_split(group, train=train, val=val, test=test, salt=salt)
        out[split].extend(members)
    return out


def assert_no_leakage(
    splits: Mapping[str, Iterable[Mapping[str, str]]],
    *,
    group_key: str,
) -> None:
    """Raise ``ValueError`` if a single ``group_key`` value appears in more than one split."""
    seen: dict[str, str] = {}
    for split_name, rows in splits.items():
        for row in rows:
            g = str(row.get(group_key, ""))
            if not g:
                continue
            if g in seen and seen[g] != split_name:
                raise ValueError(
                    f"Leakage detected: group {g!r} appears in both "
                    f"{seen[g]!r} and {split_name!r}"
                )
            seen[g] = split_name
