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


FUNCTION_DECLARATION_RE = re.compile(
    r"(?im)^[ \t]*function[ \t]+(?P<name>[A-Za-z0-9_:-]+)[ \t]*(?:\r?\n[ \t]*)?\{"
)


def _powershell_function_declarations(text: str) -> list[tuple[str, int, int]]:
    """Return PowerShell function names, source lines, and body offsets for same-line or next-line opening braces."""

    declarations: list[tuple[str, int, int]] = []
    for match in FUNCTION_DECLARATION_RE.finditer(text):
        line_number = text.count("\n", 0, match.start()) + 1
        declarations.append((match.group("name"), line_number, match.end()))
    return declarations


def _extract_powershell_help(text: str, body_offset: int) -> tuple[str, str] | None:
    """Extract SYNOPSIS and DESCRIPTION help immediately after a detected PowerShell function opening brace."""

    following = text[body_offset : body_offset + 8000].lstrip()
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


def _powershell_documentation_problems(path: Path, text: str) -> list[str]:
    """Return file- and function-level PowerShell documentation problems using multiline-safe function discovery."""

    problems: list[str] = []
    header = text[:2000]
    if not re.search(r"(?is)<#.*?\.SYNOPSIS\s+.+?\.DESCRIPTION\s+.+?#>", header):
        problems.append(f"{path.relative_to(ROOT)}:file:missing script help")

    for name, line_number, body_offset in _powershell_function_declarations(text):
        help_parts = _extract_powershell_help(text, body_offset)
        location = f"{path.relative_to(ROOT)}:{line_number}:{name}"
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
    return problems


def test_every_powershell_file_and_function_has_human_readable_help() -> None:
    """Require script-level and per-function SYNOPSIS/DESCRIPTION help with enough detail to explain behavior and failure semantics."""

    problems: list[str] = []
    for path in _powershell_paths():
        text = path.read_text(encoding="utf-8")
        problems.extend(_powershell_documentation_problems(path, text))
    assert not problems, "Insufficient PowerShell documentation: " + ", ".join(problems)


def test_powershell_function_discovery_handles_next_line_opening_brace() -> None:
    """Ensure the documentation gate discovers Allman-style PowerShell functions whose opening brace appears on the following line."""

    sample = "function Invoke-Undocumented\n{\n    param()\n}\n"
    declarations = _powershell_function_declarations(sample)
    assert declarations == [("Invoke-Undocumented", 1, sample.index("{") + 1)]
