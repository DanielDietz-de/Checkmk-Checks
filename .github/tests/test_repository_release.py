from __future__ import annotations

import ast
import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _minimal_manifest(name: str = "safe_package") -> dict[str, object]:
    return {
        "name": name,
        "title": "Test",
        "author": "Test",
        "description": "Test",
        "version": "1.0.0",
        "version.min_required": "2.4.0",
        "files": {"agents": ["plugins/test"]},
    }


def _write_manifest(package: Path, manifest: dict[str, object]) -> None:
    (package / "src").mkdir(parents=True, exist_ok=True)
    (package / "src/info").write_text(repr(manifest), encoding="utf-8")


def test_manifest_rejects_output_path_injection(tmp_path: Path) -> None:
    build = _load(
        "build_repository_mkps",
        REPOSITORY / ".github/scripts/build_repository_mkps.py",
    )
    package = tmp_path / "package"
    _write_manifest(package, _minimal_manifest("../escape"))
    with pytest.raises(ValueError, match="unsafe name"):
        build.read_manifest(package, "2.5.0p9")


def test_manifest_preserves_explicit_usable_until(tmp_path: Path) -> None:
    build = _load(
        "build_repository_mkps_explicit_cap",
        REPOSITORY / ".github/scripts/build_repository_mkps.py",
    )
    package = tmp_path / "package"
    manifest = _minimal_manifest()
    manifest["version.usable_until"] = "2.2.99"
    _write_manifest(package, manifest)

    packaged = build.read_manifest(package, "2.5.0p9")

    assert packaged["version.usable_until"] == "2.2.99"


def test_manifest_preserves_unasserted_upper_bound(tmp_path: Path) -> None:
    build = _load(
        "build_repository_mkps_default_cap",
        REPOSITORY / ".github/scripts/build_repository_mkps.py",
    )
    package = tmp_path / "package"
    _write_manifest(package, _minimal_manifest())

    packaged = build.read_manifest(package, "2.5.0p9")

    assert packaged["version.usable_until"] is None


def test_symlink_target_must_stay_in_package(tmp_path: Path) -> None:
    build = _load(
        "build_repository_mkps_symlink",
        REPOSITORY / ".github/scripts/build_repository_mkps.py",
    )
    package = tmp_path / "package"
    plugins = package / "src/agents/plugins"
    plugins.mkdir(parents=True)
    target = tmp_path / "outside"
    target.write_text("secret", encoding="utf-8")
    os.symlink(target, plugins / "escape")
    with pytest.raises(ValueError, match="absolute symlink target"):
        build._source_path(package, "agents", "plugins/escape")


def test_archive_modes_strip_special_bits(tmp_path: Path) -> None:
    build = _load(
        "build_repository_mkps_mode",
        REPOSITORY / ".github/scripts/build_repository_mkps.py",
    )
    source = tmp_path / "plugin"
    source.write_text("#!/bin/sh\n", encoding="utf-8")
    source.chmod(0o4755)
    info, file_object = build._tarinfo_for(source, "plugin")
    try:
        assert info.mode == 0o755
    finally:
        assert file_object is not None
        file_object.close()


def test_release_inventory_is_derived_from_canonical_manifests(
    tmp_path: Path,
) -> None:
    prepare = _load(
        "prepare_repository_mkp_release_inventory",
        REPOSITORY / ".github/scripts/prepare_repository_mkp_release.py",
    )
    for name in ("alpha", "beta"):
        _write_manifest(tmp_path / name, _minimal_manifest(name))

    discovered = prepare._discover_info_paths(tmp_path)

    assert [path.parent.parent.name for path in discovered] == ["alpha", "beta"]
    with pytest.raises(ValueError, match="no active package manifests"):
        prepare._discover_info_paths(tmp_path / "empty")


def test_alertmanager_source_normalization_keeps_custom_rule_namespace(
    tmp_path: Path,
) -> None:
    normalize = _load(
        "normalize_package_sources_alertmanager",
        REPOSITORY / "tools/ci/normalize_package_sources.py",
    )
    package = tmp_path / "alertmanager_extended"
    plugin = package / "src/cmk_plugins/collection/agent_based/alertmanager.py"
    ruleset = package / "src/kr_alertmanager/rulesets/alertmanager.py"
    plugin.parent.mkdir(parents=True)
    ruleset.parent.mkdir(parents=True)
    plugin.write_text(
        'check_ruleset_name="alertmanager_rule_state_custom"\n'
        'check_ruleset_name="alertmanager_rule_state_summary_custom"\n'
        '                print("got severity: %s" % severity)\n',
        encoding="utf-8",
    )
    ruleset.write_text(
        'name="alertmanager_rule_state_custom"\n'
        'name="alertmanager_rule_state_summary_custom"\n',
        encoding="utf-8",
    )
    _write_manifest(
        package,
        {
            **_minimal_manifest("alertmanager_extended"),
            "files": {
                "cmk_addons_plugins": [
                    "kr_alertmanager/rulesets/alertmanager.py"
                ]
            },
        },
    )

    changes = normalize.normalize_repository(tmp_path, write=True)

    assert changes
    assert ruleset.is_file()
    assert not (package / "src/alertmanager/rulesets/alertmanager.py").exists()
    assert "_custom" in plugin.read_text(encoding="utf-8")
    assert "print(" not in plugin.read_text(encoding="utf-8")
    assert normalize.normalize_repository(tmp_path, write=False) == []


def test_hci_choice_identifiers_are_valid() -> None:
    source = (
        REPOSITORY / "hci_cluster/src/hci_cluster/rulesets/bakery.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        function_name = (
            function.id
            if isinstance(function, ast.Name)
            else function.attr
            if isinstance(function, ast.Attribute)
            else ""
        )
        if function_name != "SingleChoiceElement":
            continue
        for keyword in node.keywords:
            if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                names.append(keyword.value.value)
    assert names
    assert all(isinstance(name, str) and name.isidentifier() for name in names)
    assert {"none", "inclusion", "exclusion"}.issubset(names)


def test_workflow_dependencies_are_immutable() -> None:
    workflow = (
        REPOSITORY / ".github/workflows/repository-mkp-ci.yml"
    ).read_text(encoding="utf-8")
    assert "actions/checkout@v6" not in workflow
    assert "actions/setup-python@v6" not in workflow
    assert "actions/upload-artifact@v7" not in workflow
    assert "actions/download-artifact@v7" not in workflow
    assert "@sha256:" in workflow
