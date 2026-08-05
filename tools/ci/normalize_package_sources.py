#!/usr/bin/env python3
"""Normalize legacy package source layouts outside the release-publication path."""

from __future__ import annotations

import argparse
import ast
import copy
import pprint
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

_BAKERY_IMPORT = "from cmk.base.cee.plugins.bakery.bakery_api.v1 import"
_BAKERY_RELATIVE_IMPORT = "from .bakery_api.v1 import"
_BAKERY_LIBRARY_ROOT = Path("lib/python3/cmk/base/cee/plugins/bakery")
_ALERTMANAGER_PACKAGE = "alertmanager_extended"
_ALERTMANAGER_PLUGIN = Path("src/cmk_plugins/collection/agent_based/alertmanager.py")
_ALERTMANAGER_RULESET = Path("src/kr_alertmanager/rulesets/alertmanager.py")
_ALERTMANAGER_MANIFEST_ENTRY = "kr_alertmanager/rulesets/alertmanager.py"
_ALERTMANAGER_DEBUG_PRINTS = (
    '                print("got severity: %s" % severity)\n',
    '                                print("set status to CRIT")\n',
    '                                print("set status to WARN")\n',
    '                                print("set status to OK")\n',
)


@dataclass(frozen=True, order=True)
class SourceChange:
    action: Literal["write", "delete"]
    path: str

    def render(self) -> str:
        return f"{self.action}: {self.path}"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--write", action="store_true")
    return parser.parse_args()


def _manifest(path: Path) -> dict[str, Any]:
    value = ast.literal_eval(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: manifest must be a dictionary")
    return copy.deepcopy(value)


def _render_manifest(manifest: dict[str, Any]) -> str:
    return pprint.pformat(manifest, sort_dicts=False, width=120) + "\n"


def _is_legacy_bakery_entry(entry: str) -> bool:
    path = Path(entry)
    return "agent_based" in path.parts and "bakery" in path.name


def _desired_bakery_state(
    package_dir: Path,
    manifest: dict[str, Any],
) -> tuple[dict[Path, str], set[Path]]:
    files = manifest.setdefault("files", {})
    if not isinstance(files, dict):
        raise ValueError(f"{package_dir}: manifest files must be a dictionary")
    addons = list(files.get("cmk_addons_plugins", []))
    if not all(isinstance(entry, str) for entry in addons):
        raise ValueError(f"{package_dir}: invalid cmk_addons_plugins entries")
    legacy_entries = [entry for entry in addons if _is_legacy_bakery_entry(entry)]
    if not legacy_entries:
        return {}, set()
    if len(legacy_entries) != 1:
        raise ValueError(
            f"{package_dir}: expected one legacy Bakery module, found {legacy_entries}"
        )

    legacy_entry = legacy_entries[0]
    source = package_dir / "src" / legacy_entry
    target_relative = _BAKERY_LIBRARY_ROOT / f"{package_dir.name}.py"
    target = package_dir / "src" / target_relative
    if source.is_file():
        content = source.read_text(encoding="utf-8")
    elif target.is_file():
        content = target.read_text(encoding="utf-8")
    else:
        raise FileNotFoundError(
            f"{package_dir}: Bakery source missing at both {source} and {target}"
        )

    if _BAKERY_IMPORT in content:
        content = content.replace(_BAKERY_IMPORT, _BAKERY_RELATIVE_IMPORT)
    elif _BAKERY_RELATIVE_IMPORT not in content:
        raise ValueError(f"{package_dir}: unsupported Bakery API import")

    files["cmk_addons_plugins"] = sorted(
        entry for entry in addons if entry != legacy_entry
    )
    library_files = list(files.get("lib", []))
    if not all(isinstance(entry, str) for entry in library_files):
        raise ValueError(f"{package_dir}: invalid lib entries")
    library_path = target_relative.relative_to("lib").as_posix()
    if library_path not in library_files:
        library_files.append(library_path)
    files["lib"] = sorted(library_files)
    return {target: content}, {source} if source != target else set()


def _desired_alertmanager_state(
    package_dir: Path,
    manifest: dict[str, Any],
) -> dict[Path, str]:
    if package_dir.name != _ALERTMANAGER_PACKAGE:
        return {}

    plugin_path = package_dir / _ALERTMANAGER_PLUGIN
    ruleset_path = package_dir / _ALERTMANAGER_RULESET
    if not plugin_path.is_file():
        raise FileNotFoundError(f"{package_dir}: Alertmanager check plug-in is missing")
    if not ruleset_path.is_file():
        raise FileNotFoundError(f"{package_dir}: Alertmanager custom ruleset is missing")

    files = manifest.setdefault("files", {})
    if not isinstance(files, dict):
        raise ValueError(f"{package_dir}: manifest files must be a dictionary")
    addons = list(files.get("cmk_addons_plugins", []))
    if _ALERTMANAGER_MANIFEST_ENTRY not in addons:
        raise ValueError(
            f"{package_dir}: manifest must retain {_ALERTMANAGER_MANIFEST_ENTRY!r}"
        )
    if "alertmanager/rulesets/alertmanager.py" in addons:
        raise ValueError(
            f"{package_dir}: built-in Alertmanager namespace must not be packaged"
        )

    ruleset_content = ruleset_path.read_text(encoding="utf-8")
    plugin_content = plugin_path.read_text(encoding="utf-8")
    for identifier in (
        "alertmanager_rule_state_custom",
        "alertmanager_rule_state_summary_custom",
    ):
        if f'name="{identifier}"' not in ruleset_content:
            raise ValueError(f"{ruleset_path}: missing custom rule declaration {identifier}")
        if f'check_ruleset_name="{identifier}"' not in plugin_content:
            raise ValueError(f"{plugin_path}: missing custom rule reference {identifier}")
    for built_in in (
        "alertmanager_rule_state",
        "alertmanager_rule_state_summary",
    ):
        if f'name="{built_in}"' in ruleset_content:
            raise ValueError(f"{ruleset_path}: duplicate built-in rule declaration {built_in}")
        if f'check_ruleset_name="{built_in}"' in plugin_content:
            raise ValueError(f"{plugin_path}: duplicate built-in rule reference {built_in}")

    desired = plugin_content
    for debug_line in _ALERTMANAGER_DEBUG_PRINTS:
        desired = desired.replace(debug_line, "")
    return {plugin_path: desired}


def normalize_repository(repository: Path, *, write: bool) -> list[SourceChange]:
    repository = repository.resolve()
    info_paths = sorted(path for path in repository.glob("*/src/info") if path.is_file())
    if not info_paths:
        raise ValueError(f"{repository}: no active package manifests found")

    changes: list[SourceChange] = []
    for info_path in info_paths:
        package_dir = info_path.parent.parent
        manifest = _manifest(info_path)
        writes, deletes = _desired_bakery_state(package_dir, manifest)
        writes.update(_desired_alertmanager_state(package_dir, manifest))
        desired_manifest = _render_manifest(manifest)
        if desired_manifest != info_path.read_text(encoding="utf-8"):
            writes[info_path] = desired_manifest

        for path, content in sorted(writes.items()):
            current = path.read_text(encoding="utf-8") if path.is_file() else None
            if current == content:
                continue
            changes.append(SourceChange("write", path.relative_to(repository).as_posix()))
            if write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        for path in sorted(deletes):
            if not path.exists():
                continue
            changes.append(SourceChange("delete", path.relative_to(repository).as_posix()))
            if write:
                path.unlink()

    return sorted(changes)


def main() -> None:
    args = _parse_args()
    changes = normalize_repository(args.repository, write=args.write)
    for change in changes:
        print(change.render())
    if changes and not args.write:
        raise SystemExit(
            f"Detected {len(changes)} pending package source normalizations; run with --write"
        )
    print(f"Package source normalization is clean ({len(changes)} changes applied)")


if __name__ == "__main__":
    main()
