#!/usr/bin/env python3
"""Parse every repository Python source without importing Checkmk modules."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Iterable

EXCLUDED_PARTS = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__", ".venv", "venv"}


def is_python_source(path: Path) -> bool:
    """Return whether *path* is Python based on suffix, legacy location, or shebang."""
    if path.suffix == ".py":
        return True
    if path.suffix or any(part in EXCLUDED_PARTS for part in path.parts):
        return False
    if path.parent.name == "checks":
        return True
    try:
        first_line = path.open("r", encoding="utf-8", errors="strict").readline()
    except (OSError, UnicodeError):
        return False
    return first_line.startswith("#!") and "python" in first_line.lower()


def iter_python_sources(root: Path) -> Iterable[Path]:
    """Yield repository Python sources in deterministic order."""
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.relative_to(root).parts):
            continue
        if is_python_source(path):
            yield path


def validate(root: Path) -> list[str]:
    """Return syntax and repository-hygiene errors for *root*."""
    errors: list[str] = []
    for path in iter_python_sources(root):
        try:
            source = path.read_text(encoding="utf-8")
            ast.parse(source, filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    count = sum(1 for _ in iter_python_sources(args.root.resolve()))
    print(f"Validated Python syntax for {count} repository source files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
