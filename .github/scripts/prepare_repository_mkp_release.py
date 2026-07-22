#!/usr/bin/env python3
"""Prepare canonical manifests and source migrations for a repository-wide MKP release."""

from __future__ import annotations

import argparse
import ast
import json
import pprint
import re
from pathlib import Path
from typing import Any

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:-dev(\d+))?")
_BAKERY_IMPORT = "from cmk.base.cee.plugins.bakery.bakery_api.v1 import"
_BAKERY_RELATIVE_IMPORT = "from .bakery_api.v1 import"
_BAKERY_LIBRARY_ROOT = Path("lib/python3/cmk/base/cee/plugins/bakery")
_ALERTMANAGER_PACKAGE = "alertmanager_extended"
_ALERTMANAGER_PLUGIN = Path("src/cmk_plugins/collection/agent_based/alertmanager.py")
_ALERTMANAGER_LEGACY_RULESET = Path("src/kr_alertmanager/rulesets/alertmanager.py")
_ALERTMANAGER_OVERRIDE_RULESET = Path("src/alertmanager/rulesets/alertmanager.py")
_ALERTMANAGER_LEGACY_MANIFEST_ENTRY = "kr_alertmanager/rulesets/alertmanager.py"
_ALERTMANAGER_OVERRIDE_MANIFEST_ENTRY = "alertmanager/rulesets/alertmanager.py"
_ALERTMANAGER_RULESET_REFERENCES = {
    'check_ruleset_name="alertmanager_rule_state_custom"':
        'check_ruleset_name="alertmanager_rule_state"',
    'check_ruleset_name="alertmanager_rule_state_summary_custom"':
        'check_ruleset_name="alertmanager_rule_state_summary"',
}
_ALERTMANAGER_RULESET_DECLARATIONS = {
    'name="alertmanager_rule_state_custom"': 'name="alertmanager_rule_state"',
    'name="alertmanager_rule_state_summary_custom"':
        'name="alertmanager_rule_state_summary"',
}
_ALERTMANAGER_DEBUG_PRINTS = (
    '                print("got severity: %s" % severity)\n',
    '                                print("set status to CRIT")\n',
    '                                print("set status to WARN")\n',
    '                                print("set status to OK")\n',
)


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


def _is_legacy_bakery_entry(entry: str) -> bool:
    path = Path(entry)
    return "agent_based" in path.parts and "bakery" in path.name


def _normalize_bakery_module(package_dir: Path, manifest: dict[str, Any]) -> list[str]:
    """Move Bakery plug-ins out of the agent-based plug-in namespace.

    Checkmk 2.4 loads Bakery extensions from the legacy Python library package
    under ``cmk.base.cee.plugins.bakery``. Files placed below an add-on family's
    ``agent_based`` directory are instead scanned as check plug-ins and fail in
    Raw/Community editions because the absolute CEE import is unavailable there.
    """

    files = manifest.setdefault("files", {})
    addons = list(files.get("cmk_addons_plugins", []))
    legacy_entries = [entry for entry in addons if _is_legacy_bakery_entry(entry)]
    if not legacy_entries:
        return []
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
        raise ValueError(
            f"{package_dir}: unsupported Bakery API import in {source if source.exists() else target}"
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    if source != target and source.exists():
        source.unlink()

    files["cmk_addons_plugins"] = sorted(
        entry for entry in addons if entry != legacy_entry
    )
    library_files = list(files.get("lib", []))
    library_path = target_relative.relative_to("lib").as_posix()
    if library_path not in library_files:
        library_files.append(library_path)
    files["lib"] = sorted(library_files)
    return [f"{legacy_entry} -> lib/{library_path}"]


def _normalize_alertmanager_override(
    package_dir: Path,
    manifest: dict[str, Any],
) -> list[str]:
    """Convert the extended Alertmanager package into a true built-in override.

    Checkmk already ships ``alertmanager_rule_state`` rulesets. A parallel
    ``*_custom`` ruleset leaves either the built-in or custom ruleset unused and
    cannot validate defaults containing the extension's ``severity_state`` key.
    Installing the extended ruleset in the same add-on family with the same base
    names lets the local package override the built-in implementation cleanly.
    """

    if package_dir.name != _ALERTMANAGER_PACKAGE:
        return []

    plugin_path = package_dir / _ALERTMANAGER_PLUGIN
    legacy_ruleset_path = package_dir / _ALERTMANAGER_LEGACY_RULESET
    override_ruleset_path = package_dir / _ALERTMANAGER_OVERRIDE_RULESET
    if not plugin_path.is_file():
        raise FileNotFoundError(f"{package_dir}: Alertmanager check plug-in is missing")

    if legacy_ruleset_path.is_file():
        ruleset_content = legacy_ruleset_path.read_text(encoding="utf-8")
    elif override_ruleset_path.is_file():
        ruleset_content = override_ruleset_path.read_text(encoding="utf-8")
    else:
        raise FileNotFoundError(f"{package_dir}: Alertmanager ruleset source is missing")

    migrations: list[str] = []
    for legacy, normalized in _ALERTMANAGER_RULESET_DECLARATIONS.items():
        if legacy in ruleset_content:
            ruleset_content = ruleset_content.replace(legacy, normalized)
            migrations.append(f"{legacy} -> {normalized}")
        elif normalized not in ruleset_content:
            raise ValueError(
                f"{legacy_ruleset_path}: neither legacy nor normalized declaration was found"
            )

    override_ruleset_path.parent.mkdir(parents=True, exist_ok=True)
    override_ruleset_path.write_text(ruleset_content, encoding="utf-8")
    if legacy_ruleset_path != override_ruleset_path and legacy_ruleset_path.exists():
        legacy_ruleset_path.unlink()
        migrations.append(
            f"{_ALERTMANAGER_LEGACY_RULESET} -> {_ALERTMANAGER_OVERRIDE_RULESET}"
        )

    files = manifest.setdefault("files", {})
    addons = list(files.get("cmk_addons_plugins", []))
    normalized_addons = [
        _ALERTMANAGER_OVERRIDE_MANIFEST_ENTRY
        if entry == _ALERTMANAGER_LEGACY_MANIFEST_ENTRY
        else entry
        for entry in addons
    ]
    if _ALERTMANAGER_OVERRIDE_MANIFEST_ENTRY not in normalized_addons:
        normalized_addons.append(_ALERTMANAGER_OVERRIDE_MANIFEST_ENTRY)
    files["cmk_addons_plugins"] = sorted(dict.fromkeys(normalized_addons))

    plugin_content = plugin_path.read_text(encoding="utf-8")
    original_plugin_content = plugin_content
    for legacy, normalized in _ALERTMANAGER_RULESET_REFERENCES.items():
        if legacy in plugin_content:
            plugin_content = plugin_content.replace(legacy, normalized)
            migrations.append(f"{legacy} -> {normalized}")
        elif normalized not in plugin_content:
            raise ValueError(
                f"{plugin_path}: neither legacy nor normalized rule reference was found"
            )

    removed_debug = 0
    for debug_line in _ALERTMANAGER_DEBUG_PRINTS:
        if debug_line in plugin_content:
            plugin_content = plugin_content.replace(debug_line, "")
            removed_debug += 1
    if removed_debug:
        migrations.append(f"removed {removed_debug} debug print statements")

    if plugin_content != original_plugin_content:
        plugin_path.write_text(plugin_content, encoding="utf-8")
    return migrations


def main() -> None:
    args = _parse_args()
    repository = args.repository.resolve()
    config_path = args.config if args.config.is_absolute() else repository / args.config
    config = _read_config(config_path)

    info_paths = sorted(repository.glob("*/src/info"))
    expected = int(config["expected_package_count"])
    if len(info_paths) != expected:
        raise SystemExit(f"Expected {expected} active packages, found {len(info_paths)}")

    bump_versions = bool(config.get("bump_versions", False))
    preserved = set(config.get("preserve_versions", []))
    packaged_version = str(config["packaged_version"])
    usable_until = str(config["usable_until"])

    changed: list[str] = []
    migrations: list[str] = []
    for info_path in info_paths:
        package_dir = info_path.parent.parent
        manifest = ast.literal_eval(info_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError(f"{info_path}: manifest must be a dictionary")

        manifest = dict(manifest)
        migrations.extend(
            f"{package_dir.name}: {entry}"
            for entry in _normalize_bakery_module(package_dir, manifest)
        )
        migrations.extend(
            f"{package_dir.name}: {entry}"
            for entry in _normalize_alertmanager_override(package_dir, manifest)
        )

        old_version = str(manifest["version"])
        if bump_versions and package_dir.name not in preserved:
            manifest["version"] = _next_version(old_version)
        else:
            manifest["version"] = old_version
        manifest["version.packaged"] = packaged_version
        manifest["version.usable_until"] = usable_until
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
    for entry in migrations:
        print(f"Applied source migration: {entry}")
    for entry in changed:
        print(entry)


if __name__ == "__main__":
    main()
