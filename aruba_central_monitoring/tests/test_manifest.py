"""Manifest and package-layout tests."""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]


def test_manifest_declares_existing_unique_files():
    manifest = ast.literal_eval((PACKAGE / "src/info").read_text(encoding="utf-8"))
    assert manifest["name"] == "aruba_central_monitoring"
    assert manifest["version.min_required"] == "2.5.0"
    declared: list[str] = []
    for category, paths in manifest["files"].items():
        assert category in {"agents", "cmk_addons_plugins"}
        declared.extend(paths)
        root = PACKAGE / "src/agents" if category == "agents" else PACKAGE / "src"
        for relative in paths:
            assert (root / relative).is_file(), relative
    assert len(declared) == len(set(declared)) == 11


def test_readme_contains_generated_reference_markers():
    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
    assert readme.count("<!-- code-derived-reference:start -->") == 1
    assert readme.count("<!-- code-derived-reference:end -->") == 1
    assert "it declares 11 packaged files" in readme
