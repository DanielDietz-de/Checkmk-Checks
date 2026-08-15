"""Regression tests for the repository-wide function documentation policy."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys


def _missing_symbols(source: str) -> list[str]:
    """Return names of undocumented functions and classes in ``source``."""
    tree = ast.parse(source)
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and ast.get_docstring(node, clean=True) is None
    ]


def _load_policy_tool():
    """Load the permanent documentation checker for behavioral regression tests."""
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


def test_undocumented_function_is_detectable() -> None:
    """Verify an undocumented function remains detectable by AST inspection."""
    assert _missing_symbols("def example():\n    return 1\n") == ["example"]


def test_documented_function_is_accepted() -> None:
    """Verify a documented function is not reported as missing documentation."""
    assert _missing_symbols('def example():\n    """Return the example result value."""\n    return 1\n') == []


def test_policy_tool_exists_in_repository() -> None:
    """Verify the permanent repository policy checker is part of the source tree."""
    assert Path("tools/ci/check_function_documentation.py").is_file()


def test_extensionless_python_shebang_is_checked(tmp_path, monkeypatch) -> None:
    """Verify extensionless Python executables remain covered by documentation policy."""
    module = _load_policy_tool()
    source = tmp_path / "agent_json"
    source.write_text("#!/usr/bin/env python3\n\nclass Endpoint:\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert any("Endpoint has no docstring" in item for item in module.collect_findings(tmp_path))


def test_powershell_function_parameters_are_checked(tmp_path, monkeypatch) -> None:
    """Verify PowerShell functions with inline parameters require purpose comments."""
    module = _load_policy_tool()
    source = tmp_path / "plugin.ps1"
    source.write_text("function rewriteOutput($output) {\n}\n", encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert any("rewriteOutput has no adjacent purpose comment" in item for item in module.collect_findings(tmp_path))


def test_powershell_modules_are_checked(tmp_path, monkeypatch) -> None:
    """Verify PowerShell module functions remain covered by documentation policy."""
    module = _load_policy_tool()
    source = tmp_path / "helpers.psm1"
    source.write_text("function Get-Example {\n}\n", encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert any("Get-Example has no adjacent purpose comment" in item for item in module.collect_findings(tmp_path))


def test_extensionless_shell_shebang_is_checked(tmp_path, monkeypatch) -> None:
    """Verify extensionless shell executables remain covered by documentation policy."""
    module = _load_policy_tool()
    source = tmp_path / "helper"
    source.write_text("#!/usr/bin/env bash\n\nrun_task() {\n    :\n}\n", encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert any("run_task has no adjacent purpose comment" in item for item in module.collect_findings(tmp_path))


def test_shell_function_keyword_without_parentheses_is_checked(tmp_path, monkeypatch) -> None:
    """Verify shell function-keyword declarations with next-line braces are checked."""
    module = _load_policy_tool()
    source = tmp_path / "helper.sh"
    source.write_text("#!/bin/bash\n\nfunction waitmax\n{\n    :\n}\n", encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert any("waitmax has no adjacent purpose comment" in item for item in module.collect_findings(tmp_path))


def test_inline_shell_function_body_is_checked(tmp_path, monkeypatch) -> None:
    """Verify one-line shell function bodies remain covered by the policy checker."""
    module = _load_policy_tool()
    source = tmp_path / "helper.sh"
    source.write_text("#!/bin/bash\n\nrun_task() { echo ready; }\n", encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert any("run_task has no adjacent purpose comment" in item for item in module.collect_findings(tmp_path))


def test_decorative_comment_does_not_satisfy_policy(tmp_path, monkeypatch) -> None:
    """Verify a decorative banner cannot masquerade as function purpose documentation."""
    module = _load_policy_tool()
    source = tmp_path / "helper.sh"
    source.write_text("#!/bin/bash\n\n# Company banner text only\n####################\n\ninpath() { :; }\n", encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert any("inpath has no adjacent purpose comment" in item for item in module.collect_findings(tmp_path))


def test_directive_comment_does_not_satisfy_policy(tmp_path, monkeypatch) -> None:
    """Verify tooling directives cannot masquerade as function purpose documentation."""
    module = _load_policy_tool()
    source = tmp_path / "helper.sh"
    source.write_text("#!/bin/bash\n\n# shellcheck disable=SC2317\nrun_task() { :; }\n", encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert any("run_task has no adjacent purpose comment" in item for item in module.collect_findings(tmp_path))


def test_adjacent_directive_blocks_earlier_purpose_text(tmp_path, monkeypatch) -> None:
    """Verify an adjacent directive cannot borrow earlier purpose text to pass policy."""
    module = _load_policy_tool()
    source = tmp_path / "helper.sh"
    source.write_text(
        "#!/bin/bash\n\n# Run the task with bounded retries.\n# shellcheck disable=SC2317\nrun_task() { :; }\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert any("run_task has no adjacent purpose comment" in item for item in module.collect_findings(tmp_path))


def test_meaningful_comment_satisfies_policy(tmp_path, monkeypatch) -> None:
    """Verify genuine adjacent purpose text satisfies non-Python documentation policy."""
    module = _load_policy_tool()
    source = tmp_path / "helper.sh"
    source.write_text("#!/bin/bash\n\n# Resolve a command from PATH safely.\ninpath() { :; }\n", encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert module.collect_findings(tmp_path) == []


def test_blank_line_breaks_purpose_comment_adjacency(tmp_path, monkeypatch) -> None:
    """Verify a blank line prevents an earlier header from documenting a declaration."""
    module = _load_policy_tool()
    source = tmp_path / "helper.sh"
    source.write_text(
        "#!/bin/bash\n\n# Describe the module and its behavior.\n\nrun_task() { :; }\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert any("run_task has no adjacent purpose comment" in item for item in module.collect_findings(tmp_path))


def test_multiline_purpose_comment_block_satisfies_policy(tmp_path, monkeypatch) -> None:
    """Verify contiguous multi-line purpose comments are evaluated as one documentation block."""
    module = _load_policy_tool()
    source = tmp_path / "helper.sh"
    source.write_text(
        "#!/bin/bash\n\n"
        "# Shell version of the waitmax utility, that limits the runtime of\n"
        "# commands. This version does not conserve the original exit code\n"
        "# of the command. It succeeds if the command terminates\n"
        "# in time.\n"
        "function waitmax\n{\n    :\n}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert module.collect_findings(tmp_path) == []


def test_punctuated_bash_function_name_is_checked(tmp_path, monkeypatch) -> None:
    """Verify Bash function names containing punctuation remain policy-visible."""
    module = _load_policy_tool()
    source = tmp_path / "helper.sh"
    source.write_text("#!/bin/bash\n\nsync-state() { echo ready; }\n", encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    assert any("sync-state has no adjacent purpose comment" in item for item in module.collect_findings(tmp_path))


def test_normalizer_documents_shell_function_keyword_form(tmp_path, monkeypatch) -> None:
    """Verify the normalizer uses the same shell declaration policy as the checker."""
    module = _load_normalizer_tool()
    source = tmp_path / "helper.sh"
    source.write_text("#!/bin/bash\n\nfunction waitmax\n{\n    :\n}\n", encoding="utf-8")
    monkeypatch.setattr(module.policy, "tracked_files", lambda _root: [source])
    counts = module.normalize_repository(tmp_path)
    assert counts["shell"] == 1
    updated = source.read_text(encoding="utf-8")
    assert "# Handle waitmax for this source file's runtime workflow.\nfunction waitmax" in updated


def test_normalizer_documents_punctuated_bash_name(tmp_path, monkeypatch) -> None:
    """Verify the normalizer documents punctuated Bash names using the shared pattern."""
    module = _load_normalizer_tool()
    source = tmp_path / "helper.sh"
    source.write_text("#!/bin/bash\n\nsync-state() { echo ready; }\n", encoding="utf-8")
    monkeypatch.setattr(module.policy, "tracked_files", lambda _root: [source])
    counts = module.normalize_repository(tmp_path)
    assert counts["shell"] == 1
    assert "# Handle sync state for this source file's runtime workflow." in source.read_text(encoding="utf-8")