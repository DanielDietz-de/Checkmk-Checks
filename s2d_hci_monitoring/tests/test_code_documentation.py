"""Human-readable function and class documentation coverage tests."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_every_python_function_and_class_has_docstring() -> None:
    """Require an explanatory docstring for every Python function and class in package source."""

    missing: list[str] = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not ast.get_docstring(node):
                missing.append(f"{path.relative_to(ROOT)}:{node.lineno}:{node.name}")
    assert not missing, "Missing Python documentation: " + ", ".join(missing)


def test_every_powershell_function_has_comment_based_help() -> None:
    """Require comment-based help immediately inside every PowerShell function body."""

    missing: list[str] = []
    for path in sorted(list((ROOT / "src").rglob("*.ps1")) + list((ROOT / "src").rglob("*.psm1")) + list((ROOT / "tools").rglob("*.ps1"))):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            match = re.match(r"\s*function\s+([A-Za-z0-9_-]+)\s*\{", line, re.IGNORECASE)
            if not match:
                continue
            following = "\n".join(lines[index + 1 : index + 10])
            if "<#" not in following or "#>" not in following:
                missing.append(f"{path.relative_to(ROOT)}:{index + 1}:{match.group(1)}")
    assert not missing, "Missing PowerShell function help: " + ", ".join(missing)
