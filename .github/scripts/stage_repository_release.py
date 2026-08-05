#!/usr/bin/env python3
"""Stage a complete validated MKP artifact set into repository source paths."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--dist", type=Path, required=True)
    return parser.parse_args()


def _active_package_dirs(repository: Path) -> set[str]:
    package_dirs = {
        path.parent.parent.name
        for path in repository.glob("*/src/info")
        if path.is_file()
    }
    if not package_dirs:
        raise ValueError(f"{repository}: no active package manifests found")
    return package_dirs


def _contained_file(root: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe relative path: {relative!r}")
    candidate = root.joinpath(*pure.parts)
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"path escapes root: {relative!r}")
    if not resolved.is_file():
        raise FileNotFoundError(candidate)
    return resolved


def _read_manifest(archive_path: Path) -> dict[str, Any]:
    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = [
            member
            for member in archive.getmembers()
            if member.isfile() and PurePosixPath(member.name).name == "info"
        ]
        if len(members) != 1:
            raise ValueError(f"{archive_path}: expected exactly one manifest, found {len(members)}")
        file_object = archive.extractfile(members[0])
        if file_object is None:
            raise ValueError(f"{archive_path}: unable to read manifest")
        payload = file_object.read().decode("utf-8")
    manifest = ast.literal_eval(payload)
    if not isinstance(manifest, dict):
        raise ValueError(f"{archive_path}: manifest is not a dictionary")
    return manifest


def _load_packages(dist: Path) -> list[dict[str, Any]]:
    value = json.loads((dist / "packages.json").read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value:
        raise ValueError(f"{dist}: packages.json must contain a non-empty list")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{dist}: every package entry must be an object")
    return value


def stage_release(repository: Path, dist: Path) -> int:
    repository = repository.resolve()
    dist = dist.resolve()
    packages = _load_packages(dist)
    active = _active_package_dirs(repository)
    indexed_dirs: set[str] = set()

    for package in packages:
        package_dir = str(package.get("package_dir", ""))
        package_name = str(package.get("name", ""))
        package_path = str(package.get("path", ""))
        package_version = str(package.get("version", ""))
        if not _SAFE_TOKEN.fullmatch(package_dir):
            raise ValueError(f"unsafe package directory: {package_dir!r}")
        if not _SAFE_TOKEN.fullmatch(package_name):
            raise ValueError(f"unsafe package name: {package_name!r}")
        if package_dir in indexed_dirs:
            raise ValueError(f"duplicate package directory: {package_dir}")
        indexed_dirs.add(package_dir)

        source = _contained_file(dist, package_path)
        checksum = _contained_file(dist, package_path + ".sha256")
        expected = checksum.read_text(encoding="utf-8").split()[0]
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        if expected != actual:
            raise ValueError(f"checksum mismatch: {source}")

        manifest = _read_manifest(source)
        if str(manifest.get("name")) != package_name:
            raise ValueError(f"{source}: manifest package name does not match packages.json")
        if str(manifest.get("version")) != package_version:
            raise ValueError(f"{source}: manifest version does not match packages.json")

        target_dir = repository / package_dir
        if target_dir.is_symlink() or not target_dir.resolve().is_relative_to(repository):
            raise ValueError(f"unsafe package target: {target_dir}")
        (target_dir / "src").mkdir(parents=True, exist_ok=True)
        for old_package in target_dir.glob("*.mkp"):
            old_package.unlink()
        for old_checksum in target_dir.glob("*.mkp.sha256"):
            old_checksum.unlink()
        (target_dir / "src" / "info").write_text(
            repr(manifest) + "\n",
            encoding="utf-8",
        )
        shutil.copy2(source, target_dir / source.name)
        shutil.copy2(checksum, target_dir / checksum.name)

    if indexed_dirs != active:
        missing = sorted(active - indexed_dirs)
        unexpected = sorted(indexed_dirs - active)
        raise ValueError(
            "artifact set is not complete: "
            f"missing={missing or 'none'}, unexpected={unexpected or 'none'}"
        )
    return len(packages)


def main() -> None:
    args = _parse_args()
    count = stage_release(args.repository, args.dist)
    print(f"Staged {count} validated packages")


if __name__ == "__main__":
    main()
