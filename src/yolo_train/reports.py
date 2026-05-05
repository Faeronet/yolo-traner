"""Markdown / JSON report writers for dataset validation and class distribution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


def write_json(path: Path | str, payload: dict) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
    return p


def write_markdown_report(path: Path | str, title: str, sections: Mapping[str, str]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    out = [f"# {title}", ""]
    for name, body in sections.items():
        out.append(f"## {name}")
        out.append(body.rstrip())
        out.append("")
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    return p


def class_distribution_table(counts: Mapping[str, int]) -> str:
    lines = ["| class | count |", "|-------|-------|"]
    for k in sorted(counts):
        lines.append(f"| {k} | {counts[k]} |")
    return "\n".join(lines)


def errors_warnings_section(errors: list[str], warnings: list[str]) -> str:
    parts: list[str] = []
    if errors:
        parts.append("### Errors")
        parts.extend(f"- {e}" for e in errors)
    else:
        parts.append("No errors.")
    if warnings:
        parts.append("")
        parts.append("### Warnings")
        parts.extend(f"- {w}" for w in warnings)
    return "\n".join(parts)
