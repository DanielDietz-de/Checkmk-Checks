"""Regression coverage for multiline named PHP function declarations."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_policy_tool():
    """Load the permanent documentation checker for PHP declaration tests."""
    path = Path("tools/ci/check_function_documentation.py")
    spec = importlib.util.spec_from_file_location("check_function_documentation", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_normalizer_tool():
    """Load the documentation normalizer with its sibling policy module available."""
    tool_dir = str(Path("tools/ci").resolve())
    sys.path.insert(0, tool_dir)
    try:
        path = Path("tools/ci/normalize_function_documentation.py")
        spec = importlib.util.spec_from_file_location("normalize_function_documentation", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(tool_dir)


def test_multiline_php_function_is_checked(tmp_path, monkeypatch) -> None:
    """Verify a named PHP function split across lines remains policy-visible."""
    module = _load_policy_tool()
    source = tmp_path / "helper.php"
    source.write_text(
        "<?php\nfunction\ncache_path() { return '/tmp'; }\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert any(
        "cache_path has no adjacent purpose comment" in item
        for item in module.collect_findings(tmp_path)
    )


def test_normalizer_documents_multiline_php_function(tmp_path, monkeypatch) -> None:
    """Verify the normalizer documents multiline PHP declarations using shared policy."""
    module = _load_normalizer_tool()
    source = tmp_path / "helper.php"
    source.write_text(
        "<?php\nfunction\ncache_path() { return '/tmp'; }\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module.policy, "tracked_files", lambda _root: [source])
    counts = module.normalize_repository(tmp_path)
    assert counts["php"] == 1
    updated = source.read_text(encoding="utf-8")
    assert "// Handle cache path for this source file's runtime workflow.\nfunction\ncache_path" in updated