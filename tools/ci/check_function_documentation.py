#!/usr/bin/env python3
"""Require human-readable documentation for every tracked named code symbol."""
from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess
import sys

MIN_DOC_WORDS = 4


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


def preceding_comment(lines: list[str], index: int) -> bool:
    """Return whether the nearest preceding non-empty line is a source comment."""
    cursor = index - 1
    while cursor >= 0 and not lines[cursor].strip():
        cursor -= 1
    if cursor < 0:
        return False
    stripped = lines[cursor].lstrip()
    return stripped.startswith(("#", "//", "/*", "*")) or stripped.endswith("*/")


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
    ps_pattern = re.compile(r"^(?P<indent>\s*)function\s+(?P<name>[A-Za-z0-9_:-]+)\b", re.I)
    sh_pattern = re.compile(
        r"^(?P<indent>\s*)(?:function\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{"
    )
    php_pattern = re.compile(
        r"^(?P<indent>\s*)(?:(?:public|protected|private|static|final|abstract)\s+)*"
        r"function\s+&?\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(",
        re.I,
    )
    for path in tracked_files(root):
        kind = source_kind(path)
        if kind == "python":
            findings.extend(check_python(path))
        elif kind == "powershell":
            findings.extend(check_pattern_file(path, ps_pattern))
        elif kind == "shell":
            findings.extend(check_pattern_file(path, sh_pattern))
        elif kind == "php":
            findings.extend(check_pattern_file(path, php_pattern))
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