#!/usr/bin/env python3
"""Prepare canonical manifests for a repository-wide MKP release."""

from __future__ import annotations

import argparse
import ast
import json
import pprint
import re
from pathlib import Path
from typing import Any

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:-dev(\d+))?")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(".github/repository-mkp-release.json"),
    )
    parser.add_argument("--complete", action="store_true")
    return parser.parse_args()


def _next_version(version: str) -> str:
    match = _VERSION_RE.fullmatch(version)
    if match is None:
        raise ValueError(f"Unsupported package version: {version!r}")
    major, minor, patch, development = match.groups()
    if development is not None:
        return f"{major}.{minor}.{patch}-dev{int(development) + 1}"
    return f"{major}.{minor}.{int(patch) + 1}"


def _read_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError(f"{path}: release configuration must be an object")
    return config


def _discover_info_paths(repository: Path) -> list[Path]:
    """Discover active packages exclusively from canonical manifests."""
    info_paths = sorted(
        path for path in repository.glob("*/src/info") if path.is_file()
    )
    if not info_paths:
        raise ValueError(f"{repository}: no active package manifests found")
    return info_paths


def _release_usable_until(manifest: dict[str, Any]) -> str | None:
    """Preserve the canonical upper compatibility claim without broadening it."""
    explicit = manifest.get("version.usable_until")
    return None if explicit is None else str(explicit)


def main() -> None:
    args = _parse_args()
    repository = args.repository.resolve()
    config_path = args.config if args.config.is_absolute() else repository / args.config
    config = _read_config(config_path)
    info_paths = _discover_info_paths(repository)

    bump_versions = bool(config.get("bump_versions", False))
    preserved = set(config.get("preserve_versions", []))
    packaged_version = str(config["packaged_version"])

    changed: list[str] = []
    for info_path in info_paths:
        package_dir = info_path.parent.parent
        manifest = ast.literal_eval(info_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError(f"{info_path}: manifest must be a dictionary")

        manifest = dict(manifest)
        old_version = str(manifest["version"])
        if bump_versions and package_dir.name not in preserved:
            manifest["version"] = _next_version(old_version)
        else:
            manifest["version"] = old_version
        manifest["version.packaged"] = packaged_version
        manifest["version.usable_until"] = _release_usable_until(manifest)
        manifest["download_url"] = (
            "https://github.com/DanielDietz-de/Checkmk-Checks/tree/master/"
            f"{package_dir.name}"
        )

        rendered = pprint.pformat(manifest, sort_dicts=False, width=120) + "\n"
        if rendered != info_path.read_text(encoding="utf-8"):
            info_path.write_text(rendered, encoding="utf-8")
            changed.append(f"{package_dir.name}: {old_version} -> {manifest['version']}")

    if args.complete and bump_versions:
        config["bump_versions"] = False
        config["completed"] = True
        config_path.write_text(
            json.dumps(config, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(f"Prepared {len(info_paths)} active package manifests")
    for entry in changed:
        print(entry)


if __name__ == "__main__":
    main()
