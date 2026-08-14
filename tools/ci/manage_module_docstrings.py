#!/usr/bin/env python3
"""Add or verify concise role-specific module docstrings in repository Python sources."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def role(path: Path, package: str) -> str:
    stem = path.stem.replace("_", " ")
    parts = set(path.parts)
    if "agent_based" in parts:
        return f"Agent-based parsing, discovery, and check logic for {package}: {stem}."
    if "server_side_calls" in parts:
        return f"Server-side command construction for the {package} integration: {stem}."
    if "rulesets" in parts:
        return f"Setup ruleset definitions for the {package} integration: {stem}."
    if "graphing" in parts:
        return f"Metric, graph, and perfometer definitions for {package}: {stem}."
    if "bakery" in parts:
        return f"Agent Bakery deployment definitions for the {package} integration: {stem}."
    if "notifications" in parts:
        return f"Notification execution logic for the {package} integration: {stem}."
    if "libexec" in parts or path.name.startswith("agent_"):
        return f"Executable data-collection helper for the {package} integration: {stem}."
    return f"Checkmk extension support code for {package}: {stem}."


def insertion_index(lines: list[str]) -> int:
    index = 0
    if lines and lines[0].startswith("#!"):
        index = 1
    if index < len(lines) and "coding" in lines[index] and lines[index].lstrip().startswith("#"):
        index += 1
    return index


EXCLUDED_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "tests", "testdata"}


def _is_python_source(path: Path) -> bool:
    if path.suffix == ".py":
        return True
    if path.suffix:
        return False
    first = path.read_bytes()[:160].decode("utf-8", errors="ignore").lower()
    return first.startswith("#!") and "python" in first.splitlines()[0]


def _component_name(root: Path, path: Path) -> str:
    relative = path.relative_to(root)
    if "src" in relative.parts:
        index = relative.parts.index("src")
        if index:
            return relative.parts[index - 1]
    return relative.parts[0] if len(relative.parts) > 1 else root.name


def run(root: Path, *, write: bool) -> list[str]:
    stale: list[str] = []
    candidates = [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not any(part in EXCLUDED_PARTS for part in path.relative_to(root).parts)
        and _is_python_source(path)
    ]
    for path in candidates:
        rel = path.relative_to(root)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            stale.append(f"{rel}: invalid UTF-8 source ({exc})")
            continue
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            continue
        if ast.get_docstring(tree, clean=False) is not None:
            continue
        if not write:
            stale.append(f"{rel}: missing module docstring")
            continue
        lines = text.splitlines(keepends=True)
        index = insertion_index(lines)
        doc = f'"""{role(path, _component_name(root, path))}"""\n\n'
        lines.insert(index, doc)
        path.write_text("".join(lines), encoding="utf-8")
    return stale


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    stale = run(args.root.resolve(), write=args.write)
    if stale:
        print("\n".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
