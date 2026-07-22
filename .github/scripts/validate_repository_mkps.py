#!/usr/bin/env python3
"""Install and validate a repository MKP set in a clean Checkmk site."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


@dataclass(frozen=True)
class CommandFailure:
    package_dir: str
    package_name: str
    package_version: str
    command: tuple[str, ...]
    returncode: int
    output: str


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


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), flush=True)
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n", flush=True)
    return completed


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


def _record_failure(
    failures: list[CommandFailure],
    package: dict[str, str],
    command: list[str],
    completed: subprocess.CompletedProcess[str],
) -> None:
    failures.append(
        CommandFailure(
            package_dir=package["package_dir"],
            package_name=package["name"],
            package_version=package["version"],
            command=tuple(command),
            returncode=completed.returncode,
            output=completed.stdout or "",
        )
    )


def _print_failures(failures: list[CommandFailure], target: str) -> None:
    print("\n=== REPOSITORY MKP VALIDATION FAILURES ===", file=sys.stderr)
    print(f"Checkmk target: {target}", file=sys.stderr)
    print(f"Failure count: {len(failures)}", file=sys.stderr)
    for index, failure in enumerate(failures, start=1):
        print(
            f"\n[{index}] {failure.package_dir} "
            f"({failure.package_name} {failure.package_version})",
            file=sys.stderr,
        )
        print(f"Command: {' '.join(failure.command)}", file=sys.stderr)
        print(f"Exit code: {failure.returncode}", file=sys.stderr)
        if failure.output:
            print("Command output:", file=sys.stderr)
            print(failure.output.rstrip(), file=sys.stderr)
    print("=== END REPOSITORY MKP VALIDATION FAILURES ===", file=sys.stderr)


def main() -> None:
    args = _parse_args()
    dist = args.dist.resolve()
    metadata = json.loads((dist / "packages.json").read_text(encoding="utf-8"))

    installed: list[dict[str, str]] = []
    manuals: set[str] = set()
    failures: list[CommandFailure] = []

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
        commands = [
            ["mkp", "inspect", str(package_path)],
            ["mkp", "add", str(package_path)],
            ["mkp", "enable", package["name"], package["version"]],
            ["mkp", "files", package["name"], package["version"]],
        ]
        package_succeeded = True
        for command in commands:
            completed = _run(command)
            if completed.returncode != 0:
                _record_failure(failures, package, command, completed)
                package_succeeded = False
                break

        if not package_succeeded:
            continue

        manuals.update(_manual_names(manifest))
        installed.append(package)

    if failures:
        _print_failures(failures, args.checkmk_version)
        raise SystemExit(1)

    global_package = {
        "package_dir": "<repository>",
        "name": "<repository>",
        "version": args.checkmk_version,
    }
    global_commands = [["cmk-validate-plugins"]]
    global_commands.extend(["cmk", "-M", manual] for manual in sorted(manuals))
    global_commands.append(["cmk", "-R"])
    for command in global_commands:
        completed = _run(command)
        if completed.returncode != 0:
            _record_failure(failures, global_package, command, completed)

    if failures:
        _print_failures(failures, args.checkmk_version)
        raise SystemExit(1)

    print(
        f"Validated {len(installed)} packages on Checkmk {args.checkmk_version}",
        flush=True,
    )


if __name__ == "__main__":
    main()
