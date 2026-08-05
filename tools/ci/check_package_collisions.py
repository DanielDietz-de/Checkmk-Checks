#!/usr/bin/env python3
"""Reject cross-package identities, file targets, and static Checkmk registrations."""

from __future__ import annotations

import argparse
import ast
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

_REGISTRATION_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "check_plugin": (
        re.compile(r"\bCheckPlugin\(\s*name\s*=\s*[\"']([^\"']+)", re.S),
        re.compile(r"\bregister\.check_plugin\([^)]*?\bname\s*=\s*[\"']([^\"']+)", re.S),
    ),
    "agent_section": (
        re.compile(r"\bAgentSection\(\s*name\s*=\s*[\"']([^\"']+)", re.S),
        re.compile(r"\bregister\.agent_section\([^)]*?\bname\s*=\s*[\"']([^\"']+)", re.S),
    ),
    "snmp_section": (
        re.compile(r"\b(?:SimpleSNMPSection|SNMPSection)\(\s*name\s*=\s*[\"']([^\"']+)", re.S),
        re.compile(r"\bregister\.snmp_section\([^)]*?\bname\s*=\s*[\"']([^\"']+)", re.S),
    ),
    "inventory_plugin": (
        re.compile(r"\bInventoryPlugin\(\s*name\s*=\s*[\"']([^\"']+)", re.S),
        re.compile(r"\bregister\.inventory_plugin\([^)]*?\bname\s*=\s*[\"']([^\"']+)", re.S),
    ),
    "special_agent": (
        re.compile(r"\bSpecialAgentConfig\(\s*name\s*=\s*[\"']([^\"']+)", re.S),
    ),
    "active_check": (
        re.compile(r"\bActiveCheckCommand\(\s*name\s*=\s*[\"']([^\"']+)", re.S),
    ),
    "check_parameters": (
        re.compile(r"\bCheckParameters\(\s*name\s*=\s*[\"']([^\"']+)", re.S),
    ),
    "agent_access": (
        re.compile(r"\bAgentAccess\(\s*name\s*=\s*[\"']([^\"']+)", re.S),
    ),
}


@dataclass(frozen=True, order=True)
class Collision:
    kind: str
    identity: str
    packages: tuple[str, ...]

    def render(self) -> str:
        return f"{self.kind} {self.identity!r} is owned by: {', '.join(self.packages)}"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path("."))
    return parser.parse_args()


def _manifest(path: Path) -> dict[str, object]:
    value = ast.literal_eval(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: manifest must be a dictionary")
    return value


def _active_packages(repository: Path) -> list[tuple[str, Path, dict[str, object]]]:
    result: list[tuple[str, Path, dict[str, object]]] = []
    for info in sorted(repository.glob("*/src/info")):
        if info.is_file():
            result.append((info.parent.parent.name, info.parent.parent, _manifest(info)))
    if not result:
        raise ValueError(f"{repository}: no active package manifests found")
    return result


def _safe_manifest_path(package: str, component: str, entry: object) -> str:
    if not isinstance(entry, str) or not entry:
        raise ValueError(f"{package}: {component} contains a non-string or empty path")
    path = PurePosixPath(entry)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{package}: unsafe {component} package path {entry!r}")
    return path.as_posix()


def _record(
    owners: dict[tuple[str, str], set[str]],
    *,
    kind: str,
    identity: str,
    package: str,
) -> None:
    owners.setdefault((kind, identity), set()).add(package)


def _registration_identities(package_dir: Path) -> Iterable[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    for path in sorted((package_dir / "src").rglob("*.py")):
        if not path.is_file() or path.name in {"info", "info.json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for kind, patterns in _REGISTRATION_PATTERNS.items():
            for pattern in patterns:
                for name in pattern.findall(text):
                    identity = (kind, name)
                    if identity not in seen:
                        seen.add(identity)
                        yield identity


def find_collisions(repository: Path) -> list[Collision]:
    owners: dict[tuple[str, str], set[str]] = {}
    for package, package_dir, manifest in _active_packages(repository.resolve()):
        name = manifest.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{package}: manifest has no valid package name")
        _record(owners, kind="package_name", identity=name, package=package)

        files = manifest.get("files", {})
        if not isinstance(files, dict):
            raise ValueError(f"{package}: manifest files must be a dictionary")
        for component, entries in files.items():
            if not isinstance(component, str) or not isinstance(entries, list):
                raise ValueError(f"{package}: invalid manifest component {component!r}")
            for entry in entries:
                normalized = _safe_manifest_path(package, component, entry)
                _record(
                    owners,
                    kind=f"packaged_path:{component}",
                    identity=normalized,
                    package=package,
                )

        for kind, identity in _registration_identities(package_dir):
            _record(owners, kind=kind, identity=identity, package=package)

    return sorted(
        Collision(kind, identity, tuple(sorted(packages)))
        for (kind, identity), packages in owners.items()
        if len(packages) > 1
    )


def main() -> None:
    args = _parse_args()
    collisions = find_collisions(args.repository)
    if collisions:
        for collision in collisions:
            print(collision.render())
        raise SystemExit(f"Detected {len(collisions)} cross-package collisions")
    print("No cross-package package-name, file-target, or static registration collisions detected")


if __name__ == "__main__":
    main()
