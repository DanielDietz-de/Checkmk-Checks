"""Regression tests for the repository-wide function documentation policy."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path


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
    source.write_text(
        "#!/usr/bin/env python3\n\nclass Endpoint:\n    pass\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    findings = module.collect_findings(tmp_path)
    assert any("Endpoint has no docstring" in finding for finding in findings)


def test_powershell_function_parameters_are_checked(tmp_path, monkeypatch) -> None:
    """Verify PowerShell functions with inline parameters require purpose comments."""
    module = _load_policy_tool()
    source = tmp_path / "plugin.ps1"
    source.write_text("function rewriteOutput($output) {\n}\n", encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    findings = module.collect_findings(tmp_path)
    assert any("rewriteOutput has no adjacent purpose comment" in finding for finding in findings)


def test_powershell_modules_are_checked(tmp_path, monkeypatch) -> None:
    """Verify PowerShell module functions remain covered by documentation policy."""
    module = _load_policy_tool()
    source = tmp_path / "helpers.psm1"
    source.write_text("function Get-Example {\n}\n", encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    findings = module.collect_findings(tmp_path)
    assert any("Get-Example has no adjacent purpose comment" in finding for finding in findings)


def test_extensionless_shell_shebang_is_checked(tmp_path, monkeypatch) -> None:
    """Verify extensionless shell executables remain covered by documentation policy."""
    module = _load_policy_tool()
    source = tmp_path / "helper"
    source.write_text("#!/usr/bin/env bash\n\nrun_task() {\n    :\n}\n", encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    findings = module.collect_findings(tmp_path)
    assert any("run_task has no adjacent purpose comment" in finding for finding in findings)