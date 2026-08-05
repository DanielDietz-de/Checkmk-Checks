#!/usr/bin/env python3
"""Verify that a staged repository release is complete, deterministic, and bounded."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

_ALLOWED_EXACT = {
    ".github/repository-mkp-release.json",
    "README.md",
    "mkp_index.json",
}
_ALLOWED_PACKAGE_PATHS = {
    "README.md",
    "src/info",
    "src/info.json",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--source-dist", type=Path, required=True)
    parser.add_argument("--rebuilt-dist", type=Path, required=True)
    return parser.parse_args()


def _load_index(dist: Path) -> list[dict[str, Any]]:
    value = json.loads((dist / "packages.json").read_text(encoding="utf-8"))
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{dist}: invalid packages.json")
    return value


def _identity(package: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(package.get("package_dir", "")),
        str(package.get("name", "")),
        str(package.get("version", "")),
        str(package.get("path", "")),
    )


def verify_artifacts(source_dist: Path, rebuilt_dist: Path) -> int:
    source = sorted((_identity(item) for item in _load_index(source_dist)))
    rebuilt = sorted((_identity(item) for item in _load_index(rebuilt_dist)))
    if source != rebuilt:
        raise ValueError("rebuilt package index does not match validated artifacts")
    for _, _, _, relative in source:
        source_path = source_dist / relative
        rebuilt_path = rebuilt_dist / relative
        if not source_path.is_file() or not rebuilt_path.is_file():
            raise FileNotFoundError(relative)
        source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        rebuilt_digest = hashlib.sha256(rebuilt_path.read_bytes()).hexdigest()
        if source_digest != rebuilt_digest:
            raise ValueError(f"nondeterministic rebuilt package: {relative}")
    return len(source)


def _changed_paths(repository: Path) -> set[str]:
    tracked = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", "HEAD"],
        cwd=repository,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.splitlines()
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repository,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.splitlines()
    return {path for path in (*tracked, *untracked) if path}


def _allowed_generated_path(path_text: str) -> bool:
    if path_text in _ALLOWED_EXACT:
        return True
    path = PurePosixPath(path_text)
    if len(path.parts) < 2:
        return False
    relative = PurePosixPath(*path.parts[1:]).as_posix()
    if relative in _ALLOWED_PACKAGE_PATHS:
        return True
    return len(path.parts) == 2 and path.name.endswith((".mkp", ".mkp.sha256"))


def verify_changed_paths(repository: Path) -> set[str]:
    changed = _changed_paths(repository)
    unexpected = sorted(path for path in changed if not _allowed_generated_path(path))
    if unexpected:
        raise ValueError(f"publication changed non-generated paths: {unexpected}")
    return changed


def verify_release_config(repository: Path) -> None:
    path = repository / ".github/repository-mkp-release.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("bump_versions") is not False or config.get("completed") is not True:
        raise ValueError("release configuration was not finalized")


def verify_release(
    repository: Path,
    source_dist: Path,
    rebuilt_dist: Path,
) -> tuple[int, set[str]]:
    repository = repository.resolve()
    verify_release_config(repository)
    changed = verify_changed_paths(repository)
    count = verify_artifacts(source_dist.resolve(), rebuilt_dist.resolve())
    subprocess.run(["git", "diff", "--check"], cwd=repository, check=True)
    return count, changed


def main() -> None:
    args = _parse_args()
    count, changed = verify_release(args.repository, args.source_dist, args.rebuilt_dist)
    print(f"Verified deterministic publication for {count} packages")
    print(f"Generated paths changed: {len(changed)}")


if __name__ == "__main__":
    main()
