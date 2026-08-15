#!/usr/bin/env python3
"""Require human-readable documentation for every tracked named code symbol."""
from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess
import sys
from typing import NamedTuple

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
PHP_MODIFIERS = frozenset(
    {"public", "protected", "private", "static", "final", "abstract"}
)


class PhpToken(NamedTuple):
    """Represent one significant PHP lexical token and its source location."""

    kind: str
    value: str
    offset: int
    line_index: int


class PhpFunctionDeclaration(NamedTuple):
    """Represent one named PHP function declaration and its source location."""

    name: str
    line_index: int
    indent: str
    offset: int


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
    """Return findings for undocumented line-oriented function declarations."""
    findings: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        match = pattern.search(line)
        if match and not preceding_comment(lines, index):
            findings.append(
                f"{path}:{index + 1}: {match.group('name')} has no adjacent purpose comment"
            )
    return findings


def _php_identifier_start(char: str) -> bool:
    """Return whether one character may start a PHP identifier."""
    return char == "_" or char.isalpha() or ord(char) >= 0x80


def _php_identifier_continue(char: str) -> bool:
    """Return whether one character may continue a PHP identifier."""
    return char == "_" or char.isalnum() or ord(char) >= 0x80


def _skip_php_quoted(text: str, offset: int, quote: str) -> int:
    """Return the offset immediately after one quoted PHP string."""
    cursor = offset + 1
    while cursor < len(text):
        char = text[cursor]
        if char == "\\":
            cursor += 2
            continue
        cursor += 1
        if char == quote:
            break
    return min(cursor, len(text))


def _parse_php_heredoc_label(text: str, offset: int) -> tuple[str, int] | None:
    """Return a heredoc label and body offset when opener syntax is recognizable."""
    cursor = offset + 3
    while cursor < len(text) and text[cursor] in " \t":
        cursor += 1
    quote: str | None = None
    if cursor < len(text) and text[cursor] in {"'", '"'}:
        quote = text[cursor]
        cursor += 1
    if cursor >= len(text) or not _php_identifier_start(text[cursor]):
        return None
    start = cursor
    cursor += 1
    while cursor < len(text) and _php_identifier_continue(text[cursor]):
        cursor += 1
    label = text[start:cursor]
    if quote is not None:
        if cursor >= len(text) or text[cursor] != quote:
            return None
        cursor += 1
    while cursor < len(text) and text[cursor] in " \t":
        cursor += 1
    if cursor < len(text) and text[cursor] == "\r":
        cursor += 1
    if cursor >= len(text) or text[cursor] != "\n":
        return None
    return label, cursor + 1


def _skip_php_heredoc(text: str, offset: int) -> int | None:
    """Return the offset after one heredoc or nowdoc body when recognized."""
    parsed = _parse_php_heredoc_label(text, offset)
    if parsed is None:
        return None
    label, cursor = parsed
    while cursor < len(text):
        line_end = text.find("\n", cursor)
        if line_end < 0:
            line_end = len(text)
            next_line = len(text)
        else:
            next_line = line_end + 1
        raw = text[cursor:line_end]
        if raw.endswith("\r"):
            raw = raw[:-1]
        stripped = raw.lstrip(" \t")
        if stripped.startswith(label):
            remainder = stripped[len(label) :].lstrip(" \t")
            if not remainder or not _php_identifier_continue(remainder[0]):
                return next_line
        cursor = next_line
    return len(text)


def php_tokens(text: str) -> list[PhpToken]:
    """Return significant PHP tokens while excluding comments, strings, and heredocs."""
    tokens: list[PhpToken] = []
    offset = 0
    line_index = 0
    in_php = False
    while offset < len(text):
        if not in_php:
            if text.startswith("<?php", offset):
                in_php = True
                offset += 5
                continue
            if text.startswith("<?=", offset):
                in_php = True
                offset += 3
                continue
            if text.startswith("<?", offset):
                in_php = True
                offset += 2
                continue
            if text[offset] == "\n":
                line_index += 1
            offset += 1
            continue

        if text.startswith("?>", offset):
            in_php = False
            offset += 2
            continue
        char = text[offset]
        if char in " \t\r":
            offset += 1
            continue
        if char == "\n":
            line_index += 1
            offset += 1
            continue
        if text.startswith("//", offset) or (
            char == "#" and not text.startswith("#[", offset)
        ):
            end = text.find("\n", offset)
            if end < 0:
                break
            offset = end
            continue
        if text.startswith("/*", offset):
            end = text.find("*/", offset + 2)
            if end < 0:
                break
            end += 2
            line_index += text.count("\n", offset, end)
            offset = end
            continue
        if char in {"'", '"', "`"}:
            end = _skip_php_quoted(text, offset, char)
            line_index += text.count("\n", offset, end)
            offset = end
            continue
        if text.startswith("<<<", offset):
            end = _skip_php_heredoc(text, offset)
            if end is not None:
                line_index += text.count("\n", offset, end)
                offset = end
                continue
        if _php_identifier_start(char):
            start = offset
            token_line = line_index
            offset += 1
            while offset < len(text) and _php_identifier_continue(text[offset]):
                offset += 1
            tokens.append(PhpToken("identifier", text[start:offset], start, token_line))
            continue
        tokens.append(PhpToken("punctuation", char, offset, line_index))
        offset += 1
    return tokens


def _php_attribute_start(tokens: list[PhpToken], closing_index: int) -> int | None:
    """Return the opening attribute token index for one closing bracket."""
    depth = 0
    cursor = closing_index
    while cursor >= 0:
        value = tokens[cursor].value
        if value == "]":
            depth += 1
        elif value == "[":
            depth -= 1
            if depth == 0:
                if cursor > 0 and tokens[cursor - 1].value == "#":
                    return cursor - 1
                return None
        cursor -= 1
    return None


def php_function_declarations(text: str) -> list[PhpFunctionDeclaration]:
    """Return actual named PHP function declarations from lexically significant tokens."""
    tokens = php_tokens(text)
    declarations: list[PhpFunctionDeclaration] = []
    for index, token in enumerate(tokens):
        if token.kind != "identifier" or token.value.casefold() != "function":
            continue
        cursor = index + 1
        if cursor < len(tokens) and tokens[cursor].value == "&":
            cursor += 1
        if cursor >= len(tokens) or tokens[cursor].kind != "identifier":
            continue
        name = tokens[cursor].value
        if cursor + 1 >= len(tokens) or tokens[cursor + 1].value != "(":
            continue

        start_index = index
        before = index - 1
        while (
            before >= 0
            and tokens[before].kind == "identifier"
            and tokens[before].value.casefold() in PHP_MODIFIERS
        ):
            start_index = before
            before -= 1
        while before >= 0 and tokens[before].value == "]":
            attribute_start = _php_attribute_start(tokens, before)
            if attribute_start is None:
                break
            start_index = attribute_start
            before = attribute_start - 1

        start = tokens[start_index]
        line_start = text.rfind("\n", 0, start.offset) + 1
        prefix = text[line_start : start.offset]
        indent = prefix if not prefix.strip() else ""
        declarations.append(
            PhpFunctionDeclaration(name, start.line_index, indent, start.offset)
        )
    return declarations


def check_php(path: Path) -> list[str]:
    """Return documentation findings for actual named PHP function declarations."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    findings: list[str] = []
    for declaration in php_function_declarations(text):
        if not preceding_comment(lines, declaration.line_index):
            findings.append(
                f"{path}:{declaration.line_index + 1}: {declaration.name} "
                "has no adjacent purpose comment"
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
            findings.extend(check_php(path))
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