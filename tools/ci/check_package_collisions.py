#!/usr/bin/env python3
"""Reject cross-package identities, file targets, and static Checkmk registrations."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

_CLASS_REGISTRATIONS = {
    "CheckPlugin": "check_plugin",
    "AgentSection": "agent_section",
    "SimpleSNMPSection": "snmp_section",
    "SNMPSection": "snmp_section",
    "InventoryPlugin": "inventory_plugin",
    "SpecialAgentConfig": "special_agent",
    "ActiveCheckCommand": "active_check",
    "CheckParameters": "check_parameters",
    "AgentAccess": "agent_access",
}
_LEGACY_REGISTRATIONS = {
    "register.check_plugin": "check_plugin",
    "register.agent_section": "agent_section",
    "register.snmp_section": "snmp_section",
    "register.inventory_plugin": "inventory_plugin",
    "register.active_check": "active_check",
}


@dataclass(frozen=True, order=True)
class Collision:
    """Represent collision behavior and associated state."""
    kind: str
    identity: str
    packages: tuple[str, ...]

    def render(self) -> str:
        """Handle render for this module's workflow."""
        return f"{self.kind} {self.identity!r} is owned by: {', '.join(self.packages)}"


def _parse_args() -> argparse.Namespace:
    """Handle parse args for this module's workflow."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path("."))
    return parser.parse_args()


def _manifest(path: Path) -> dict[str, object]:
    """Handle manifest for this module's workflow."""
    value = ast.literal_eval(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: manifest must be a dictionary")
    return value


def _active_packages(repository: Path) -> list[tuple[str, Path, dict[str, object]]]:
    """Handle active packages for this module's workflow."""
    result: list[tuple[str, Path, dict[str, object]]] = []
    for info in sorted(repository.glob("*/src/info")):
        if info.is_file():
            result.append((info.parent.parent.name, info.parent.parent, _manifest(info)))
    if not result:
        raise ValueError(f"{repository}: no active package manifests found")
    return result


def _safe_manifest_path(package: str, component: str, entry: object) -> str:
    """Handle safe manifest path for this module's workflow."""
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
    """Handle record for this module's workflow."""
    owners.setdefault((kind, identity), set()).add(package)


def _call_name(node: ast.expr) -> str:
    """Handle call name for this module's workflow."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _literal_name(call: ast.Call) -> str | None:
    """Handle literal name for this module's workflow."""
    for keyword in call.keywords:
        if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
            value = keyword.value.value
            return value if isinstance(value, str) and value else None
    return None


def _registration_kind(function_name: str) -> str | None:
    """Handle registration kind for this module's workflow."""
    legacy = _LEGACY_REGISTRATIONS.get(function_name)
    if legacy is not None:
        return legacy
    return _CLASS_REGISTRATIONS.get(function_name.rsplit(".", maxsplit=1)[-1])


def _registration_identities(package_dir: Path) -> Iterable[tuple[str, str]]:
    """Handle registration identities for this module's workflow."""
    seen: set[tuple[str, str]] = set()
    for path in sorted((package_dir / "src").rglob("*.py")):
        if not path.is_file() or path.name in {"info", "info.json"}:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            raise ValueError(f"{path}: unable to inspect registrations: {exc}") from exc
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            kind = _registration_kind(_call_name(node.func))
            name = _literal_name(node)
            if kind is None or name is None:
                continue
            identity = (kind, name)
            if identity not in seen:
                seen.add(identity)
                yield identity


def find_collisions(repository: Path) -> list[Collision]:
    """Handle find collisions for this module's workflow."""
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
    """Run the command-line entry point and return its result."""
    args = _parse_args()
    collisions = find_collisions(args.repository)
    if collisions:
        for collision in collisions:
            print(collision.render())
        raise SystemExit(f"Detected {len(collisions)} cross-package collisions")
    print("No cross-package package-name, file-target, or static registration collisions detected")


if __name__ == "__main__":
    main()
