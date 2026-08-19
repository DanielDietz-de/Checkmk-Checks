"""Regression coverage for shell arithmetic and continued declarations."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_policy_tool():
    """Load the permanent documentation checker for shell regression tests."""
    path = Path("tools/ci/check_function_documentation.py")
    spec = importlib.util.spec_from_file_location("check_function_documentation", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_normalizer_tool():
    """Load the documentation normalizer with its policy module available."""
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


def _findings(module, tmp_path, monkeypatch, source_text: str) -> list[str]:
    """Return documentation findings for one temporary shell source file."""
    source = tmp_path / "helper.sh"
    source.write_text(source_text, encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    return module.collect_findings(tmp_path)


def test_shell_backslash_continued_declaration_is_detected(tmp_path, monkeypatch) -> None:
    """Verify backslash-newline declarations remain visible to the policy scanner."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "#!/bin/bash\nundocumented_helper\\\n() { :; }\n",
    )
    assert any("undocumented_helper has no adjacent purpose comment" in item for item in findings)


def test_shell_normalizer_repairs_backslash_continued_declaration(
    tmp_path, monkeypatch
) -> None:
    """Verify normalization repairs a function split by backslash-newline."""
    module = _load_normalizer_tool()
    source = tmp_path / "helper.sh"
    source.write_text(
        "#!/bin/bash\nundocumented_helper\\\n() { :; }\n", encoding="utf-8"
    )
    monkeypatch.setattr(module.policy, "tracked_files", lambda _root: [source])
    counts = module.normalize_repository(tmp_path)
    assert counts["shell"] == 1
    assert "# Handle undocumented helper" in source.read_text(encoding="utf-8")


def test_shell_legacy_arithmetic_shift_does_not_start_heredoc(
    tmp_path, monkeypatch
) -> None:
    """Verify legacy Bash arithmetic shifts do not hide later declarations."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "#!/bin/bash\nvalue=$[1 << 2]\nundocumented_helper() { :; }\n",
    )
    assert any("undocumented_helper has no adjacent purpose comment" in item for item in findings)


def test_shell_normalizer_survives_legacy_arithmetic_shift(
    tmp_path, monkeypatch
) -> None:
    """Verify normalization sees functions after legacy Bash arithmetic shifts."""
    module = _load_normalizer_tool()
    source = tmp_path / "helper.sh"
    source.write_text(
        "#!/bin/bash\nvalue=$[1 << 2]\nundocumented_helper() { :; }\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module.policy, "tracked_files", lambda _root: [source])
    counts = module.normalize_repository(tmp_path)
    assert counts["shell"] == 1
