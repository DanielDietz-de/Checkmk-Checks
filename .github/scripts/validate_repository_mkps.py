#!/usr/bin/env python3
"""Install and validate a repository MKP set in a clean Checkmk site."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--checkmk-version", required=True)
    return parser.parse_args()


def _version_key(value: str) -> tuple[int, int, int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:(b|rc|p)(\d+))?", value)
    if not match:
        raise ValueError(f"Unsupported Checkmk version: {value!r}")
    major, minor, patch = (int(match.group(index)) for index in (1, 2, 3))
    suffix = match.group(4)
    suffix_number = int(match.group(5) or 0)
    rank = {"b": 0, "rc": 1, None: 2, "p": 3}[suffix]
    return major, minor, patch, rank, suffix_number


def _supports_target(min_required: str, target: str) -> bool:
    return _version_key(min_required) <= _version_key(target)


def _run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def _manifest(package_path: Path) -> dict[str, Any]:
    with tarfile.open(package_path, mode="r:gz") as archive:
        member = next(
            (item for item in archive.getmembers() if PurePosixPath(item.name).name == "info"),
            None,
        )
        if member is None:
            raise ValueError(f"{package_path}: missing info")
        fileobj = archive.extractfile(member)
        if fileobj is None:
            raise ValueError(f"{package_path}: unreadable info")
        manifest = ast.literal_eval(fileobj.read().decode("utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"{package_path}: invalid manifest")
    return manifest


def _manual_names(manifest: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    files = manifest.get("files", {})
    for path in files.get("checkman", []):
        names.add(PurePosixPath(path).name)
    for path in files.get("cmk_addons_plugins", []):
        relative = PurePosixPath(path)
        if "checkman" in relative.parts:
            names.add(relative.name)
    return names


def main() -> None:
    args = _parse_args()
    dist = args.dist.resolve()
    metadata = json.loads((dist / "packages.json").read_text(encoding="utf-8"))

    installed: list[dict[str, str]] = []
    manuals: set[str] = set()
    for package in metadata:
        if not _supports_target(package["min_required"], args.checkmk_version):
            print(
                f"Skipping {package['name']} {package['version']} on {args.checkmk_version}: "
                f"requires {package['min_required']}",
                flush=True,
            )
            continue

        package_path = dist / package["path"]
        manifest = _manifest(package_path)
        if manifest.get("name") != package["name"] or str(manifest.get("version")) != package["version"]:
            raise ValueError(f"{package_path}: metadata index mismatch")

        print(
            f"Validating {package['name']} {package['version']} from {package['package_dir']}",
            flush=True,
        )
        try:
            _run(["mkp", "inspect", str(package_path)])
            _run(["mkp", "add", str(package_path)])
            _run(["mkp", "enable", package["name"], package["version"]])
            _run(["mkp", "files", package["name"], package["version"]])
        except subprocess.CalledProcessError as exc:
            raise SystemExit(
                f"Package installation failed for {package['package_dir']} "
                f"({package['name']} {package['version']}): {exc}"
            ) from exc

        manuals.update(_manual_names(manifest))
        installed.append(package)

    _run(["cmk-validate-plugins"])
    for manual in sorted(manuals):
        _run(["cmk", "-M", manual])
    _run(["cmk", "-R"])

    print(
        f"Validated {len(installed)} packages on Checkmk {args.checkmk_version}",
        flush=True,
    )


if __name__ == "__main__":
    main()
