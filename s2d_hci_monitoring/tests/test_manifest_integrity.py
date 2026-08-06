"""Verify that the canonical manifest matches the migrated package tree."""

from __future__ import annotations

import ast
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _manifest() -> dict[str, object]:
    value = ast.literal_eval((PACKAGE_ROOT / "src" / "info").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_manifest_identity_and_compatibility():
    manifest = _manifest()
    assert manifest["name"] == "s2d_hci_monitoring"
    assert manifest["version"] == "1.0.0"
    assert manifest["version.min_required"] == "2.5.0"
    assert manifest["version.usable_until"] == "2.5.99"


def test_every_manifest_file_exists():
    manifest = _manifest()
    files = manifest["files"]
    assert isinstance(files, dict)

    category_roots = {
        "agents": PACKAGE_ROOT / "src" / "agents",
        "cmk_addons_plugins": PACKAGE_ROOT / "src",
    }
    for category, entries in files.items():
        assert category in category_roots
        assert isinstance(entries, list)
        for entry in entries:
            assert (category_roots[category] / entry).is_file(), f"Missing manifest file: {category}/{entry}"


def test_manifest_has_no_duplicate_paths():
    manifest = _manifest()
    files = manifest["files"]
    declared = [(category, entry) for category, entries in files.items() for entry in entries]
    assert len(declared) == len(set(declared))


def test_package_license_is_preserved():
    text = (PACKAGE_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "PolyForm Internal Use License 1.0.0" in text
