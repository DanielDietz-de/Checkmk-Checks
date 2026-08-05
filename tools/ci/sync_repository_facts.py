#!/usr/bin/env python3
"""Synchronize repository-level package counts from canonical manifests."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


TARGETS = (
    (
        Path("README.md"),
        re.compile(r"(currently discovers \*\*)\d+( active packages\*\*)"),
    ),
    (
        Path("docs/REPOSITORY_AUDIT.md"),
        re.compile(r"(covers \*\*)\d+( active packages\*\*)"),
    ),
)


def active_package_count(root: Path) -> int:
    """Count active packages from canonical top-level manifests."""
    return sum(1 for path in root.glob("*/src/info") if path.is_file())


def run(root: Path, *, write: bool) -> list[str]:
    """Validate or rewrite every repository-level package-count claim."""
    count = active_package_count(root)
    stale: list[str] = []
    for relative, pattern in TARGETS:
        path = root / relative
        text = path.read_text(encoding="utf-8")
        expected, replacements = pattern.subn(rf"\g<1>{count}\g<2>", text)
        if replacements != 1:
            stale.append(f"{relative}: expected exactly one package-count marker")
            continue
        if text == expected:
            continue
        if write:
            path.write_text(expected, encoding="utf-8")
        else:
            stale.append(
                f"{relative}: package count is stale; expected {count} active packages"
            )
    return stale


def main(argv: list[str] | None = None) -> int:
    """Run the repository-fact synchronization command."""
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
