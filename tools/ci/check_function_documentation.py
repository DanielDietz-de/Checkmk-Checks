#!/usr/bin/env python3
"""Require human-readable documentation for every tracked named code symbol."""
from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess
import sys

MIN_DOC_WORDS = 4
PURPOSE_COMMENT_MIN_WORDS = 4
DIRECTIVE_COMMENT_RE = re.compile(
    r"^(?:shellcheck\b|noqa\b|ruff\b|pylint\b|mypy\b|pyright\b|"
    r"type\s*:\s*ignore\b|pragma\b|fmt\s*:|region\b|endregion\b|debug\b)",
    re.I,
)
POWERSHELL_FUNCTION_PATTERN = re.compile(
    r"^(?P<indent>\s*)function\s+(?P<name>[A-Za-z0-9_:-]+)\b", re.I
)
SHELL_FUNCTION_NAME = r"[^\s(){};=<>]+"
SHELL_FUNCTION_PATTERN = re.compile(
    r"^(?P<indent>\s*)"
    r"(?=(?:function\s+|" + SHELL_FUNCTION_NAME + r"\s*\(\s*\)))"
    r"(?:function\s+)?(?P<name>" + SHELL_FUNCTION_NAME + r")"
    r"\s*(?:\(\s*\))?(?=\s|\{|$)"
)
PHP_FUNCTION_PATTERN = re.compile(
    r"^(?P<indent>\s*)(?:(?:public|protected|private|static|final|abstract)\s+)*"
    r"function\s+&?\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(",
    re.I,
)


def tracked_files(root: Path) -> list[Path]:
    """Return all tracked files in the repository."""
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [root / raw.decode("utf-8") for raw in completed.stdout.split(b"\0") if raw]


def source_kind(path: Path) -> str | None:
    """Return the supported source language identified by extension or shebang."""
    suffix = path.suffix.lower()
    extension_kinds = {
        ".py": "python",
        ".ps1": "powershell",
        ".psm1": "powershell",
        ".sh": "shell",
        ".php": "php",
    }
    if suffix in extension_kinds:
        return extension_kinds[suffix]
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            first_line = handle.readline(512).strip().lower()
    except (OSError, UnicodeDecodeError):
        return None
    if not first_line.startswith("#!"):
        return None
    if re.search(r"(?:^|[/\s])python(?:\d+(?:\.\d+)*)?(?:\s|$)", first_line):
        return "python"
    if re.search(r"(?:^|[/\s])(?:pwsh|powershell)(?:\s|$)", first_line):
        return "powershell"
    if re.search(r"(?:^|[/\s])(?:ba|da|z|k)?sh(?:\s|$)", first_line):
        return "shell"
    if re.search(r"(?:^|[/\s])php(?:\s|$)", first_line):
        return "php"
    return None


def check_python(path: Path) -> list[str]:
    """Return documentation findings for one Python source file."""
    findings: list[str] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except UnicodeDecodeError as exc:
        return [f"{path}: invalid UTF-8 source: {exc}"]
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        doc = ast.get_docstring(node, clean=True)
        if not doc:
            findings.append(f"{path}:{node.lineno}: {node.name} has no docstring")
            continue
        if len(re.findall(r"[A-Za-z0-9]+", doc)) < MIN_DOC_WORDS:
            findings.append(f"{path}:{node.lineno}: {node.name} docstring is too terse")
    return findings


def _strip_block_comment(lines: list[str], cursor: int) -> str | None:
    """Return the nearest meaningful segment of an adjacent C-style comment block."""
    collected: list[str] = []
    found_start = False
    while cursor >= 0:
        raw = lines[cursor].strip()
        collected.append(raw)
        if "/*" in raw:
            found_start = True
            break
        cursor -= 1
    if not found_start:
        return None

    parts: list[str] = []
    delimiter_only = {"/*", "/**", "*/", "*"}
    for raw in collected:
        if raw in delimiter_only:
            continue
        cleaned = raw.replace("/*", " ").replace("*/", " ").strip()
        cleaned = cleaned.lstrip("*").strip()
        if _comment_block_boundary(cleaned):
            if not parts:
                return cleaned or None
            break
        parts.append(cleaned)
    return " ".join(reversed(parts)) if parts else None


def _clean_line_comment(raw: str, marker: str) -> str:
    """Remove a line-comment marker and decorative trailing markers from one line."""
    stripped = raw.lstrip()
    if not stripped.startswith(marker):
        return ""
    cleaned = stripped[len(marker) :].strip()
    if marker == "#":
        cleaned = cleaned.rstrip("#").strip()
    return cleaned


def _comment_block_boundary(text: str) -> bool:
    """Return whether comment text must stop purpose-block aggregation."""
    if not text or not re.search(r"[A-Za-z0-9]", text):
        return True
    if DIRECTIVE_COMMENT_RE.match(text):
        return True
    return bool(re.fullmatch(r"https?://\S+", text, re.I))


def _line_comment_block(lines: list[str], cursor: int, marker: str) -> str | None:
    """Return a contiguous line-comment purpose block ending at ``cursor``."""
    nearest = _clean_line_comment(lines[cursor], marker)
    if _comment_block_boundary(nearest):
        return nearest or None

    parts = [nearest]
    cursor -= 1
    while cursor >= 0:
        stripped = lines[cursor].lstrip()
        if not stripped.startswith(marker) or stripped.startswith("#!"):
            break
        text = _clean_line_comment(lines[cursor], marker)
        if _comment_block_boundary(text):
            break
        parts.append(text)
        cursor -= 1
    return " ".join(reversed(parts))


def preceding_comment_text(lines: list[str], index: int) -> str | None:
    """Return normalized text from the directly adjacent purpose-comment block."""
    if index <= 0:
        return None
    cursor = index - 1
    if not lines[cursor].strip():
        return None
    stripped = lines[cursor].lstrip().strip()
    if stripped.startswith("#!"):
        return None
    if stripped.startswith("#"):
        return _line_comment_block(lines, cursor, "#")
    if stripped.startswith("//"):
        return _line_comment_block(lines, cursor, "//")
    if stripped.endswith("*/") or stripped.startswith("/*"):
        return _strip_block_comment(lines, cursor)
    return None


def meaningful_purpose_comment(text: str | None) -> bool:
    """Return whether adjacent comment text contains actual purpose documentation."""
    if not text:
        return False
    normalized = " ".join(text.split()).strip()
    if not normalized or DIRECTIVE_COMMENT_RE.match(normalized):
        return False
    if re.fullmatch(r"https?://\S+", normalized, re.I):
        return False
    return len(re.findall(r"[A-Za-z0-9]+", normalized)) >= PURPOSE_COMMENT_MIN_WORDS


def preceding_comment(lines: list[str], index: int) -> bool:
    """Return whether a declaration has a directly adjacent meaningful purpose comment."""
    return meaningful_purpose_comment(preceding_comment_text(lines, index))


def check_pattern_file(path: Path, pattern: re.Pattern[str]) -> list[str]:
    """Return findings for undocumented non-Python function declarations."""
    findings: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        match = pattern.search(line)
        if match and not preceding_comment(lines, index):
            findings.append(
                f"{path}:{index + 1}: {match.group('name')} has no adjacent purpose comment"
            )
    return findings


def collect_findings(root: Path) -> list[str]:
    """Collect documentation findings from all tracked supported source files."""
    findings: list[str] = []
    for path in tracked_files(root):
        kind = source_kind(path)
        if kind == "python":
            findings.extend(check_python(path))
        elif kind == "powershell":
            findings.extend(check_pattern_file(path, POWERSHELL_FUNCTION_PATTERN))
        elif kind == "shell":
            findings.extend(check_pattern_file(path, SHELL_FUNCTION_PATTERN))
        elif kind == "php":
            findings.extend(check_pattern_file(path, PHP_FUNCTION_PATTERN))
    return findings


def main() -> int:
    """Report all code-documentation violations and return a failing status if any exist."""
    root = Path.cwd()
    findings = collect_findings(root)
    if findings:
        print("Function-level documentation policy failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1
    print("Function-level documentation policy passed for all tracked supported source files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())