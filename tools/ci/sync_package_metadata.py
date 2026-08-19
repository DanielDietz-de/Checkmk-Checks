#!/usr/bin/env python3
"""Validate and synchronize MKP metadata mirrors from canonical ``src/info`` files."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = (
    "name",
    "title",
    "description",
    "version",
    "version.min_required",
    "version.packaged",
    "version.usable_until",
    "files",
)


def load_manifest(path: Path) -> dict[str, Any]:
    """Load manifest from its configured source."""
    value = ast.literal_eval(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: manifest must contain a dictionary")
    return value


def validate_manifest(path: Path, data: dict[str, Any]) -> list[str]:
    """Validate manifest and reject invalid input."""
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"{path}: missing {field!r}")
            continue
        value = data[field]
        if field == "files":
            if not isinstance(value, dict) or not value:
                errors.append(f"{path}: {field!r} must be a non-empty mapping")
        elif field == "version.usable_until":
            if value is not None and (not isinstance(value, str) or not value.strip()):
                errors.append(f"{path}: {field!r} must be null or a non-empty string")
        elif not isinstance(value, str) or not value.strip():
            errors.append(f"{path}: {field!r} must be a non-empty string")
    return errors


def rendered_json(data: dict[str, Any]) -> str:
    """Handle rendered json for this module's workflow."""
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def run(root: Path, *, write: bool) -> list[str]:
    """Handle run for this module's workflow."""
    errors: list[str] = []
    for manifest in sorted(root.glob("*/src/info")):
        try:
            data = load_manifest(manifest)
        except (OSError, SyntaxError, ValueError) as exc:
            errors.append(str(exc))
            continue
        errors.extend(validate_manifest(manifest.relative_to(root), data))
        mirror = manifest.with_name("info.json")
        if not mirror.exists():
            continue
        expected = rendered_json(data)
        actual = mirror.read_text(encoding="utf-8")
        if actual == expected:
            continue
        if write:
            mirror.write_text(expected, encoding="utf-8")
        else:
            errors.append(
                f"{mirror.relative_to(root)}: does not exactly mirror canonical {manifest.relative_to(root)}"
            )
    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse args into its normalized representation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--write", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the command-line entry point and return its result."""
    args = parse_args(argv)
    errors = run(args.root.resolve(), write=args.write)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
