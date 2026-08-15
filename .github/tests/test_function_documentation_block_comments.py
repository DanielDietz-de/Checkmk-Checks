"""Regression coverage for block-comment purpose documentation boundaries."""
from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_policy_tool():
    """Load the permanent documentation checker for focused regression tests."""
    path = Path("tools/ci/check_function_documentation.py")
    spec = importlib.util.spec_from_file_location("check_function_documentation", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phpdoc_purpose_block_satisfies_policy(tmp_path, monkeypatch) -> None:
    """Verify a directly adjacent PHPDoc purpose block satisfies the policy."""
    module = _load_policy_tool()
    source = tmp_path / "helper.php"
    source.write_text(
        "<?php\n"
        "/**\n"
        " * Return the configured application cache path.\n"
        " */\n"
        "function cache_path() { return '/tmp'; }\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert module.collect_findings(tmp_path) == []


def test_block_directive_cannot_borrow_earlier_purpose(tmp_path, monkeypatch) -> None:
    """Verify a trailing directive prevents earlier block prose from satisfying policy."""
    module = _load_policy_tool()
    source = tmp_path / "helper.php"
    source.write_text(
        "<?php\n"
        "/*\n"
        " * Describe the task and its purpose.\n"
        " * pragma: generated code\n"
        " */\n"
        "function run_task() { return true; }\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert any("run_task has no adjacent purpose comment" in item for item in module.collect_findings(tmp_path))


def test_block_decorator_cannot_borrow_earlier_purpose(tmp_path, monkeypatch) -> None:
    """Verify a trailing decorative line prevents earlier block prose from passing."""
    module = _load_policy_tool()
    source = tmp_path / "helper.php"
    source.write_text(
        "<?php\n"
        "/*\n"
        " * Describe the task and its purpose.\n"
        " * ********************\n"
        " */\n"
        "function run_task() { return true; }\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert any("run_task has no adjacent purpose comment" in item for item in module.collect_findings(tmp_path))