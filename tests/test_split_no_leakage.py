"""Verify that splitting by group keeps each group inside a single split."""

from __future__ import annotations

from collections import defaultdict

import pytest

from yolo_train.splitting import (
    assert_no_leakage,
    assign_split,
    split_by_group,
    stable_hash,
)


def test_stable_hash_is_deterministic() -> None:
    a = stable_hash("foo")
    b = stable_hash("foo")
    assert a == b


def test_assign_split_distributes() -> None:
    counts: dict[str, int] = defaultdict(int)
    for i in range(2000):
        counts[assign_split(f"doc-{i}", train=0.8, val=0.1, test=0.1)] += 1
    total = sum(counts.values())
    assert counts["train"] / total > 0.7
    assert counts["val"] / total > 0.05
    assert counts["test"] / total > 0.05


def test_split_by_group_keeps_groups_together() -> None:
    items = []
    for doc in range(50):
        for page in range(5):
            items.append({"page_id": f"d{doc}-p{page}", "group": f"d{doc}"})

    out = split_by_group(items, group_key="group", train=0.8, val=0.1, test=0.1)
    seen: dict[str, str] = {}
    for split, rows in out.items():
        for row in rows:
            g = row["group"]
            if g in seen:
                assert seen[g] == split, f"Group {g} leaked between splits"
            seen[g] = split
    assert_no_leakage(out, group_key="group")


def test_assert_no_leakage_raises() -> None:
    bad = {
        "train": [{"page_id": "p1", "group": "g1"}],
        "val": [{"page_id": "p2", "group": "g1"}],
        "test": [],
    }
    with pytest.raises(ValueError):
        assert_no_leakage(bad, group_key="group")
