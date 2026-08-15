"""Regression tests for the repository-wide function documentation policy."""
from __future__ import annotations

import ast
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


def test_undocumented_function_is_detectable() -> None:
    """Verify an undocumented function remains detectable by AST inspection."""
    assert _missing_symbols("def example():\n    return 1\n") == ["example"]


def test_documented_function_is_accepted() -> None:
    """Verify a documented function is not reported as missing documentation."""
    assert _missing_symbols('def example():\n    """Return the example result value."""\n    return 1\n') == []


def test_policy_tool_exists_in_repository() -> None:
    """Verify the permanent repository policy checker is part of the source tree."""
    assert Path("tools/ci/check_function_documentation.py").is_file()
