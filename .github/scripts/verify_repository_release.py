#!/usr/bin/env python3
"""Verify that a staged repository release is complete, deterministic, and bounded."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--source-dist", type=Path, required=True)
    parser.add_argument("--rebuilt-dist", type=Path, required=True)
    return parser.parse_args()


def _load_index(dist: Path) -> list[dict[str, Any]]:
    value = json.loads((dist / "packages.json").read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value:
        raise ValueError(f"{dist}: packages.json must contain a non-empty list")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{dist}: every package index entry must be an object")
    return value


def _identity(package: dict[str, Any]) -> tuple[str, str, str, str]:
    package_dir = str(package.get("package_dir", ""))
    package_name = str(package.get("name", ""))
    package_version = str(package.get("version", ""))
    relative = str(package.get("path", ""))
    for label, value in (
        ("package directory", package_dir),
        ("package name", package_name),
        ("package version", package_version),
    ):
        if not _SAFE_TOKEN.fullmatch(value):
            raise ValueError(f"unsafe {label}: {value!r}")
    expected = f"{package_dir}/{package_name}-{package_version}.mkp"
    if relative != expected:
        raise ValueError(f"unexpected package path {relative!r}; expected {expected!r}")
    return package_dir, package_name, package_version, relative


def _validated_identities(dist: Path) -> list[tuple[str, str, str, str]]:
    identities = [_identity(item) for item in _load_index(dist)]
    if len(set(identities)) != len(identities):
        raise ValueError(f"{dist}: duplicate package index identity")
    package_dirs = [identity[0] for identity in identities]
    if len(set(package_dirs)) != len(package_dirs):
        raise ValueError(f"{dist}: duplicate package directory")
    return sorted(identities)


def _contained_file(root: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe relative path: {relative!r}")
    candidate = root.joinpath(*pure.parts)
    if candidate.is_symlink():
        raise ValueError(f"artifact path must not be a symlink: {relative!r}")
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"artifact path escapes root: {relative!r}")
    if not resolved.is_file():
        raise FileNotFoundError(candidate)
    return resolved


def verify_artifacts(source_dist: Path, rebuilt_dist: Path) -> int:
    source_dist = source_dist.resolve()
    rebuilt_dist = rebuilt_dist.resolve()
    source = _validated_identities(source_dist)
    rebuilt = _validated_identities(rebuilt_dist)
    if source != rebuilt:
        raise ValueError("rebuilt package index does not match validated artifacts")
    for _, _, _, relative in source:
        source_path = _contained_file(source_dist, relative)
        rebuilt_path = _contained_file(rebuilt_dist, relative)
        source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        rebuilt_digest = hashlib.sha256(rebuilt_path.read_bytes()).hexdigest()
        if source_digest != rebuilt_digest:
            raise ValueError(f"nondeterministic rebuilt package: {relative}")
    return len(source)


def _decode_nul_paths(data: bytes) -> set[str]:
    fields = data.decode("utf-8", errors="strict").split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    return {field for field in fields if field}


def _changed_paths(repository: Path) -> set[str]:
    tracked = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", "-z", "HEAD"],
        cwd=repository,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=repository,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    return _decode_nul_paths(tracked) | _decode_nul_paths(untracked)


def _active_package_dirs(repository: Path) -> set[str]:
    package_dirs = {
        path.parent.parent.name
        for path in repository.glob("*/src/info")
        if path.is_file()
    }
    if not package_dirs:
        raise ValueError(f"{repository}: no active package manifests found")
    return package_dirs


def _allowed_generated_path(path_text: str, active_packages: set[str]) -> bool:
    path = PurePosixPath(path_text)
    if path.is_absolute() or ".." in path.parts:
        return False
    if path_text in _ALLOWED_EXACT:
        return True
    if len(path.parts) < 2 or path.parts[0] not in active_packages:
        return False
    relative = PurePosixPath(*path.parts[1:]).as_posix()
    if relative in _ALLOWED_PACKAGE_PATHS:
        return True
    return len(path.parts) == 2 and path.name.endswith((".mkp", ".mkp.sha256"))


def verify_changed_paths(repository: Path) -> set[str]:
    changed = _changed_paths(repository)
    active_packages = _active_package_dirs(repository)
    unexpected = sorted(
        path
        for path in changed
        if not _allowed_generated_path(path, active_packages)
    )
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
    count = verify_artifacts(source_dist, rebuilt_dist)
    subprocess.run(
        ["git", "diff", "--check"],
        cwd=repository,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return count, changed


def main() -> None:
    args = _parse_args()
    count, changed = verify_release(args.repository, args.source_dist, args.rebuilt_dist)
    print(f"Verified deterministic publication for {count} packages")
    print(f"Generated paths changed: {len(changed)}")


if __name__ == "__main__":
    main()
