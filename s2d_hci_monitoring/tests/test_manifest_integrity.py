"""Validate canonical package manifest ownership, version metadata, removed legacy collectors, and the exact runtime source-file inventory."""

from __future__ import annotations

import ast
from pathlib import Path


def _manifest() -> dict[str, object]:
    """Load the literal Checkmk package manifest without executing code."""

    root = Path(__file__).resolve().parents[1]
    return ast.literal_eval((root / "src/info").read_text(encoding="utf-8"))


def test_manifest_declares_version_1_1_0_and_exact_files() -> None:
    """Every manifest-owned file must exist and obsolete performance code must be absent."""

    root = Path(__file__).resolve().parents[1]
    manifest = _manifest()
    assert manifest["version"] == "1.1.0"
    declared = []
    for category, paths in manifest["files"].items():
        for path in paths:
            declared.append((category, path))
            if category == "lib":
                source = root / "src/lib" / path
            elif category == "cmk_addons_plugins":
                source = root / "src" / path
            else:
                source = root / "src/agents" / path
            assert source.is_file(), source
    assert len(declared) == 21
    assert all("perf" not in path for _, path in declared)
    assert not (root / "src/agents/plugins/s2d_hci_perf.ps1").exists()
    assert not (root / "src/s2d_hci/agent_based/s2d_hci_perf.py").exists()


def test_manifest_contains_bakery_and_protocol_components() -> None:
    """Production packaging must include Bakery, shared protocol, and collector-health support."""

    manifest = _manifest()
    agents = set(manifest["files"]["agents"])
    addons = set(manifest["files"]["cmk_addons_plugins"])
    libs = set(manifest["files"]["lib"])
    assert "bin/s2d_hci_common.psm1" in agents
    assert "s2d_hci/agent_based/s2d_hci_collector_health.py" in addons
    assert "s2d_hci/rulesets/bakery.py" in addons
    assert "python3/cmk/base/cee/plugins/bakery/s2d_hci.py" in libs
