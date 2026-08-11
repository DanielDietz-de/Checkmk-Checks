"""Enforce human-readable module, function, class, and PowerShell help documentation."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON_WORDS = 8
MIN_PYTHON_CHARS = 50
MIN_PS_SYNOPSIS_WORDS = 5
MIN_PS_DESCRIPTION_WORDS = 10
PLACEHOLDERS = {"todo", "tbd", "fixme", "document me"}


def _python_paths() -> list[Path]:
    """Return every package Python source and test file whose documentation is part of the maintained code contract."""

    return sorted(list((ROOT / "src").rglob("*.py")) + list((ROOT / "tests").rglob("*.py")))


def _powershell_paths() -> list[Path]:
    """Return every production or lifecycle PowerShell file that must carry operator-readable comment-based help."""

    return sorted(
        list((ROOT / "src").rglob("*.ps1"))
        + list((ROOT / "src").rglob("*.psm1"))
        + list((ROOT / "tools").rglob("*.ps1"))
    )


def _documentation_problem(text: str) -> str | None:
    """Return a reason when documentation is absent, placeholder-like, or too terse to explain the symbol meaningfully."""

    normalized = " ".join(text.split()).strip()
    if not normalized:
        return "missing"
    lowered = normalized.lower()
    if any(marker in lowered for marker in PLACEHOLDERS):
        return "contains placeholder text"
    if len(normalized) < MIN_PYTHON_CHARS:
        return f"shorter than {MIN_PYTHON_CHARS} characters"
    if len(normalized.split()) < MIN_PYTHON_WORDS:
        return f"fewer than {MIN_PYTHON_WORDS} words"
    return None


def test_every_python_module_function_and_class_is_human_readable() -> None:
    """Require meaningful documentation for every Python module, function, method, and class in source and focused tests."""

    problems: list[str] = []
    for path in _python_paths():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module_problem = _documentation_problem(ast.get_docstring(tree) or "")
        if module_problem:
            problems.append(f"{path.relative_to(ROOT)}:module:{module_problem}")
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            problem = _documentation_problem(ast.get_docstring(node) or "")
            if problem:
                problems.append(
                    f"{path.relative_to(ROOT)}:{node.lineno}:{node.name}:{problem}"
                )
    assert not problems, "Insufficient Python documentation: " + ", ".join(problems)


def _extract_powershell_help(lines: list[str], function_index: int) -> tuple[str, str] | None:
    """Extract the leading SYNOPSIS and DESCRIPTION bodies from the comment-based help immediately inside a PowerShell function."""

    following = "\n".join(lines[function_index + 1 : function_index + 40]).lstrip()
    if not following.startswith("<#"):
        return None
    block_match = re.match(r"<#(?P<body>.*?)#>", following, re.DOTALL)
    if not block_match:
        return None
    body = block_match.group("body")
    synopsis_match = re.search(
        r"(?is)\.SYNOPSIS\s*(?P<text>.*?)(?=\n\s*\.DESCRIPTION\b)", body
    )
    description_match = re.search(
        r"(?is)\.DESCRIPTION\s*(?P<text>.*?)(?=\n\s*\.[A-Z][A-Z0-9_-]*\b|\Z)",
        body,
    )
    if not synopsis_match or not description_match:
        return None
    synopsis = " ".join(synopsis_match.group("text").split())
    description = " ".join(description_match.group("text").split())
    return synopsis, description


def test_every_powershell_file_and_function_has_human_readable_help() -> None:
    """Require script-level and per-function SYNOPSIS/DESCRIPTION help with enough detail to explain behavior and failure semantics."""

    problems: list[str] = []
    for path in _powershell_paths():
        text = path.read_text(encoding="utf-8")
        header = text[:2000]
        if not re.search(r"(?is)<#.*?\.SYNOPSIS\s+.+?\.DESCRIPTION\s+.+?#>", header):
            problems.append(f"{path.relative_to(ROOT)}:file:missing script help")

        lines = text.splitlines()
        for index, line in enumerate(lines):
            match = re.match(r"\s*function\s+([A-Za-z0-9_-]+)\s*\{", line, re.IGNORECASE)
            if not match:
                continue
            help_parts = _extract_powershell_help(lines, index)
            location = f"{path.relative_to(ROOT)}:{index + 1}:{match.group(1)}"
            if help_parts is None:
                problems.append(f"{location}:missing .SYNOPSIS/.DESCRIPTION")
                continue
            synopsis, description = help_parts
            if len(synopsis.split()) < MIN_PS_SYNOPSIS_WORDS:
                problems.append(
                    f"{location}:synopsis has fewer than {MIN_PS_SYNOPSIS_WORDS} words"
                )
            if len(description.split()) < MIN_PS_DESCRIPTION_WORDS:
                problems.append(
                    f"{location}:description has fewer than {MIN_PS_DESCRIPTION_WORDS} words"
                )
            combined = f"{synopsis} {description}".lower()
            if any(marker in combined for marker in PLACEHOLDERS):
                problems.append(f"{location}:contains placeholder text")
    assert not problems, "Insufficient PowerShell documentation: " + ", ".join(problems)
