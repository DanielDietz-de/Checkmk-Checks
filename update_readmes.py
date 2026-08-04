#!/usr/bin/env python3
"""Synchronize README compatibility badges from explicit MKP metadata.

The script deliberately does not infer compatibility from importability, the
minimum version, package layout, or another package. Only metadata explicitly
present in src/info or src/info.json is rendered.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

START = "<!-- compatibility-badges:start -->"
END = "<!-- compatibility-badges:end -->"
METADATA_FIELDS = (
    "name",
    "version",
    "version.min_required",
    "version.packaged",
    "version.usable_until",
)


class MetadataError(RuntimeError):
    """Raised when package metadata cannot be trusted."""


@dataclass(frozen=True)
class PackageMetadata:
    directory: Path
    data: dict[str, Any]
    sources: tuple[Path, ...]


def _load_python_metadata(path: Path) -> dict[str, Any]:
    try:
        value = ast.literal_eval(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError, ValueError, TypeError) as exc:
        raise MetadataError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MetadataError(f"{path} does not contain a dictionary")
    return value


def _load_json_metadata(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MetadataError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MetadataError(f"{path} does not contain an object")
    return value


def _validate_metadata(data: dict[str, Any], source: Path) -> None:
    for field in ("name", "version"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            raise MetadataError(f"{source}: missing non-empty {field}")
    for field in METADATA_FIELDS[2:]:
        value = data.get(field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise MetadataError(f"{source}: {field} must be a non-empty string")


def load_package_metadata(package_dir: Path) -> PackageMetadata | None:
    info = package_dir / "src" / "info"
    info_json = package_dir / "src" / "info.json"
    sources: list[Path] = []
    records: list[dict[str, Any]] = []
    if info.is_file():
        records.append(_load_python_metadata(info))
        sources.append(info)
    if info_json.is_file():
        records.append(_load_json_metadata(info_json))
        sources.append(info_json)
    if not records:
        return None
    for record, source in zip(records, sources):
        _validate_metadata(record, source)

    canonical = records[0]
    for other, source in zip(records[1:], sources[1:]):
        for field in METADATA_FIELDS:
            if canonical.get(field) != other.get(field):
                raise MetadataError(
                    f"metadata mismatch for {package_dir.name}: {field} differs "
                    f"between {sources[0]} and {source}"
                )
    return PackageMetadata(package_dir, canonical, tuple(sources))


def discover_packages(root: Path) -> list[PackageMetadata]:
    packages: list[PackageMetadata] = []
    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or directory.name.startswith("."):
            continue
        metadata = load_package_metadata(directory)
        if metadata is not None:
            packages.append(metadata)
    return packages


def badge(label: str, message: str, color: str) -> str:
    return (
        f"![{label}](https://img.shields.io/badge/"
        f"{quote(label)}-{quote(message)}-{color})"
    )


def build_block(info: dict[str, Any]) -> str:
    badges: list[str] = []
    minimum = info.get("version.min_required")
    packaged = info.get("version.packaged")
    usable_until = info.get("version.usable_until")
    if minimum:
        badges.append(badge("Checkmk min", minimum, "2f4f4f"))
    if packaged:
        badges.append(badge("packaged", packaged, "blue"))
    if usable_until:
        badges.append(badge("usable until", usable_until, "green"))
    return f"{START}\n{' '.join(badges)}\n{END}" if badges else ""


def inject(readme_text: str, block: str, title: str) -> str:
    start_index = readme_text.find(START)
    end_index = readme_text.find(END)
    if (start_index == -1) != (end_index == -1):
        raise MetadataError("README has incomplete compatibility badge markers")
    if start_index != -1:
        end_index += len(END)
        return readme_text[:start_index] + block + readme_text[end_index:]
    if not block:
        return readme_text
    lines = readme_text.splitlines(keepends=True)
    if lines and lines[0].startswith("#"):
        return "".join(lines[:1]) + "\n" + block + "\n" + "".join(lines[1:])
    return f"# {title}\n\n{block}\n\n{readme_text}"


def create(info: dict[str, Any], block: str) -> str:
    title = info.get("title", info.get("name", "Plugin"))
    description = str(info.get("description", "")).rstrip()
    return f"# {title}\n\n{block}\n\n{description}\n"


def validate_legacy_cap(metadata: PackageMetadata) -> list[str]:
    files = metadata.data.get("files")
    if not isinstance(files, dict):
        return []
    legacy_categories = {"agent_based", "checkman", "web", "lib"}
    used = sorted(legacy_categories.intersection(files))
    if used and not metadata.data.get("version.usable_until"):
        return [
            f"{metadata.directory.name}: legacy file categories {', '.join(used)} "
            "have no explicit version.usable_until"
        ]
    return []


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--strict-legacy-caps", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    created: list[str] = []
    updated: list[str] = []
    drift: list[Path] = []
    warnings: list[str] = []
    try:
        for metadata in discover_packages(args.root):
            warnings.extend(validate_legacy_cap(metadata))
            readme = metadata.directory / "README.md"
            block = build_block(metadata.data)
            title = metadata.data.get("title", metadata.data["name"])
            if readme.exists():
                old = readme.read_text(encoding="utf-8")
                new = inject(old, block, str(title))
                if new != old:
                    if args.check:
                        drift.append(readme)
                    else:
                        readme.write_text(new, encoding="utf-8")
                        updated.append(metadata.directory.name)
            elif not args.check:
                readme.write_text(create(metadata.data, block), encoding="utf-8")
                created.append(metadata.directory.name)
            else:
                drift.append(readme)
    except MetadataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if args.strict_legacy_caps and warnings:
        return 2
    if args.check and drift:
        for path in drift:
            print(f"README compatibility badges are stale: {path}", file=sys.stderr)
        return 1
    print(f"Created {len(created)}:")
    for name in created:
        print(f"  + {name}")
    print(f"Updated {len(updated)}:")
    for name in updated:
        print(f"  ~ {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
