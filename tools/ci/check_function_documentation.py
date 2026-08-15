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


class LineFunctionDeclaration(NamedTuple):
    """Represent one line-oriented function declaration and source location."""

    name: str
    line_index: int
    indent: str


class PhpToken(NamedTuple):
    """Represent one significant PHP lexical token and its source location."""

    kind: str
    value: str
    offset: int
    line_index: int


class PhpComment(NamedTuple):
    """Represent one lexical PHP comment and its physical source span."""

    marker: str
    text: str
    start_line: int
    end_line: int
    full_line: bool


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


def _purpose_from_line_comments(
    declaration_line: int, comments: dict[int, str]
) -> bool:
    """Return whether lexical line comments directly document one declaration."""
    cursor = declaration_line - 1
    if cursor not in comments:
        return False
    nearest = comments[cursor]
    if _comment_block_boundary(nearest):
        return meaningful_purpose_comment(nearest)
    parts = [nearest]
    cursor -= 1
    while cursor in comments:
        text = comments[cursor]
        if _comment_block_boundary(text):
            break
        parts.append(text)
        cursor -= 1
    return meaningful_purpose_comment(" ".join(reversed(parts)))


def _parse_shell_heredoc_operator(
    line: str, offset: int
) -> tuple[str, bool, int] | None:
    """Return one shell heredoc delimiter parsed from an unquoted operator."""
    if not line.startswith("<<", offset) or line.startswith("<<<", offset):
        return None
    cursor = offset + 2
    strip_tabs = False
    if cursor < len(line) and line[cursor] == "-":
        strip_tabs = True
        cursor += 1
    while cursor < len(line) and line[cursor] in " \t":
        cursor += 1
    if cursor >= len(line):
        return None
    if line[cursor] in {"'", '"'}:
        quote = line[cursor]
        cursor += 1
        start = cursor
        while cursor < len(line) and line[cursor] != quote:
            cursor += 1
        if cursor >= len(line):
            return None
        delimiter = line[start:cursor]
        return delimiter, strip_tabs, cursor + 1
    start = cursor
    while cursor < len(line) and line[cursor] not in " \t;&|()<>\r\n":
        cursor += 1
    raw = line[start:cursor]
    delimiter = raw.replace("\\", "")
    if not delimiter:
        return None
    return delimiter, strip_tabs, cursor


def _scan_shell(
    text: str,
) -> tuple[list[LineFunctionDeclaration], dict[int, str]]:
    """Return shell declarations and full-line lexical comments outside literals."""
    declarations: list[LineFunctionDeclaration] = []
    comments: dict[int, str] = {}
    heredocs: list[tuple[str, bool]] = []
    quote: str | None = None
    for line_index, line in enumerate(text.splitlines()):
        if heredocs:
            delimiter, strip_tabs = heredocs[0]
            candidate = line.lstrip("\t") if strip_tabs else line
            if candidate == delimiter:
                heredocs.pop(0)
            continue

        chars = list(line)
        first_nonspace = len(line) - len(line.lstrip(" \t"))
        cursor = 0
        while cursor < len(line):
            char = line[cursor]
            if quote is not None:
                chars[cursor] = " "
                if quote in {'"', "`"} and char == "\\":
                    if cursor + 1 < len(line):
                        chars[cursor + 1] = " "
                    cursor += 2
                    continue
                if char == quote:
                    quote = None
                cursor += 1
                continue
            if char in {"'", '"', "`"}:
                quote = char
                chars[cursor] = " "
                cursor += 1
                continue
            if char == "#":
                if cursor == first_nonspace:
                    comments[line_index] = line[cursor + 1 :].strip().rstrip("#").strip()
                for index in range(cursor, len(chars)):
                    chars[index] = " "
                break
            if line.startswith("<<", cursor):
                parsed = _parse_shell_heredoc_operator(line, cursor)
                if parsed is not None:
                    delimiter, strip_tabs, end = parsed
                    heredocs.append((delimiter, strip_tabs))
                    cursor = end
                    continue
            cursor += 1
        sanitized = "".join(chars)
        match = SHELL_FUNCTION_PATTERN.search(sanitized)
        if match:
            declarations.append(
                LineFunctionDeclaration(
                    match.group("name"), line_index, match.group("indent") or ""
                )
            )
    return declarations, comments


def shell_function_declarations(text: str) -> list[LineFunctionDeclaration]:
    """Return actual shell function declarations outside literal regions."""
    return _scan_shell(text)[0]


def shell_declaration_has_purpose(
    text: str, declaration: LineFunctionDeclaration
) -> bool:
    """Return whether lexical shell comments document one function declaration."""
    _, comments = _scan_shell(text)
    return _purpose_from_line_comments(declaration.line_index, comments)


def _scan_powershell(
    text: str,
) -> tuple[list[LineFunctionDeclaration], dict[int, str]]:
    """Return PowerShell declarations and comments outside literal regions."""
    declarations: list[LineFunctionDeclaration] = []
    comments: dict[int, str] = {}
    here_string: str | None = None
    block_comment = False
    quote: str | None = None
    for line_index, line in enumerate(text.splitlines()):
        if here_string is not None:
            if line.strip() == here_string + "@":
                here_string = None
            continue

        chars = list(line)
        first_nonspace = len(line) - len(line.lstrip(" \t"))
        cursor = 0
        while cursor < len(line):
            char = line[cursor]
            if block_comment:
                chars[cursor] = " "
                if line.startswith("#>", cursor):
                    chars[cursor] = chars[cursor + 1] = " "
                    block_comment = False
                    cursor += 2
                    continue
                cursor += 1
                continue
            if quote is not None:
                chars[cursor] = " "
                if quote == '"' and char == "`":
                    if cursor + 1 < len(line):
                        chars[cursor + 1] = " "
                    cursor += 2
                    continue
                if (
                    quote == "'"
                    and char == "'"
                    and cursor + 1 < len(line)
                    and line[cursor + 1] == "'"
                ):
                    chars[cursor + 1] = " "
                    cursor += 2
                    continue
                if char == quote:
                    quote = None
                cursor += 1
                continue
            if line.startswith("<#", cursor):
                chars[cursor] = chars[cursor + 1] = " "
                block_comment = True
                cursor += 2
                continue
            if line.startswith('@"', cursor) or line.startswith("@'", cursor):
                here_string = line[cursor + 1]
                for index in range(cursor, len(chars)):
                    chars[index] = " "
                break
            if char in {"'", '"'}:
                quote = char
                chars[cursor] = " "
                cursor += 1
                continue
            if char == "#":
                if cursor == first_nonspace:
                    comments[line_index] = line[cursor + 1 :].strip().rstrip("#").strip()
                for index in range(cursor, len(chars)):
                    chars[index] = " "
                break
            cursor += 1
        sanitized = "".join(chars)
        match = POWERSHELL_FUNCTION_PATTERN.search(sanitized)
        if match:
            declarations.append(
                LineFunctionDeclaration(
                    match.group("name"), line_index, match.group("indent") or ""
                )
            )
    return declarations, comments


def powershell_function_declarations(text: str) -> list[LineFunctionDeclaration]:
    """Return actual PowerShell function declarations outside literal regions."""
    return _scan_powershell(text)[0]


def powershell_declaration_has_purpose(
    text: str, declaration: LineFunctionDeclaration
) -> bool:
    """Return whether lexical PowerShell comments document one function declaration."""
    _, comments = _scan_powershell(text)
    return _purpose_from_line_comments(declaration.line_index, comments)


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
    """Return the offset immediately after a heredoc or nowdoc terminator label."""
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
            remainder = stripped[len(label) :]
            if not remainder or not _php_identifier_continue(remainder[0]):
                indentation = len(raw) - len(stripped)
                return cursor + indentation + len(label)
        cursor = next_line
    return len(text)


def _php_line_prefix_is_whitespace(text: str, offset: int) -> bool:
    """Return whether only indentation precedes one offset on its physical line."""
    line_start = text.rfind("\n", 0, offset) + 1
    return not text[line_start:offset].strip()


def _php_line_suffix_is_whitespace(text: str, offset: int) -> bool:
    """Return whether only whitespace follows one offset on its physical line."""
    line_end = text.find("\n", offset)
    if line_end < 0:
        line_end = len(text)
    return not text[offset:line_end].strip()


def _php_lex(text: str) -> tuple[list[PhpToken], list[PhpComment]]:
    """Return PHP code tokens and lexical comments while excluding literal regions."""
    tokens: list[PhpToken] = []
    comments: list[PhpComment] = []
    offset = 0
    line_index = 0
    in_php = False
    while offset < len(text):
        if not in_php:
            if text[offset : offset + 5].casefold() == "<?php":
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
            marker = "//" if text.startswith("//", offset) else "#"
            marker_length = len(marker)
            newline = text.find("\n", offset)
            closing_tag = text.find("?>", offset + marker_length)
            if closing_tag >= 0 and (newline < 0 or closing_tag < newline):
                end = closing_tag
                closes_php = True
            else:
                end = newline if newline >= 0 else len(text)
                closes_php = False
            full_line = _php_line_prefix_is_whitespace(text, offset) and not closes_php
            comments.append(
                PhpComment(
                    marker,
                    text[offset + marker_length : end].strip(),
                    line_index,
                    line_index,
                    full_line,
                )
            )
            if closes_php:
                offset = closing_tag
                continue
            if newline < 0:
                break
            offset = newline
            continue
        if text.startswith("/*", offset):
            end = text.find("*/", offset + 2)
            if end < 0:
                break
            end += 2
            start_line = line_index
            end_line = line_index + text.count("\n", offset, end)
            full_line = _php_line_prefix_is_whitespace(
                text, offset
            ) and _php_line_suffix_is_whitespace(text, end)
            comments.append(
                PhpComment("/*", text[offset:end], start_line, end_line, full_line)
            )
            line_index = end_line
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
    return tokens, comments


def php_tokens(text: str) -> list[PhpToken]:
    """Return significant PHP tokens outside comments and literal regions."""
    return _php_lex(text)[0]


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


def _php_function_declarations_from_tokens(
    text: str, tokens: list[PhpToken]
) -> list[PhpFunctionDeclaration]:
    """Return named PHP declarations from an existing significant-token stream."""
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


def php_function_declarations(text: str) -> list[PhpFunctionDeclaration]:
    """Return actual named PHP declarations from lexical PHP tokens."""
    tokens, _ = _php_lex(text)
    return _php_function_declarations_from_tokens(text, tokens)


def _php_comment_has_purpose(
    declaration: PhpFunctionDeclaration, comments: list[PhpComment]
) -> bool:
    """Return whether lexical PHP comments directly document one declaration."""
    candidates = [
        comment
        for comment in comments
        if comment.full_line and comment.end_line == declaration.line_index - 1
    ]
    if not candidates:
        return False
    nearest = candidates[-1]
    if nearest.marker == "/*":
        lines = nearest.text.splitlines()
        return meaningful_purpose_comment(
            _strip_block_comment(lines, len(lines) - 1) if lines else None
        )

    nearest_text = nearest.text.strip()
    if nearest.marker == "#":
        nearest_text = nearest_text.rstrip("#").strip()
    if _comment_block_boundary(nearest_text):
        return meaningful_purpose_comment(nearest_text)
    parts = [nearest_text]
    current_line = nearest.start_line
    comments_by_end_line = {
        comment.end_line: comment for comment in comments if comment.full_line
    }
    while current_line - 1 in comments_by_end_line:
        comment = comments_by_end_line[current_line - 1]
        if comment.marker != nearest.marker:
            break
        text = comment.text.strip()
        if comment.marker == "#":
            text = text.rstrip("#").strip()
        if _comment_block_boundary(text):
            break
        parts.append(text)
        current_line = comment.start_line
    return meaningful_purpose_comment(" ".join(reversed(parts)))


def php_declaration_has_purpose(
    text: str, declaration: PhpFunctionDeclaration
) -> bool:
    """Return whether a named PHP declaration has lexical purpose documentation."""
    _, comments = _php_lex(text)
    return _php_comment_has_purpose(declaration, comments)


def check_line_declarations(
    path: Path,
    declarations: list[LineFunctionDeclaration],
    purpose_checker,
) -> list[str]:
    """Return findings for undocumented shell-like function declarations."""
    text = path.read_text(encoding="utf-8")
    findings: list[str] = []
    for declaration in declarations:
        if not purpose_checker(text, declaration):
            findings.append(
                f"{path}:{declaration.line_index + 1}: {declaration.name} "
                "has no adjacent purpose comment"
            )
    return findings


def check_php(path: Path) -> list[str]:
    """Return documentation findings for actual named PHP function declarations."""
    text = path.read_text(encoding="utf-8")
    tokens, comments = _php_lex(text)
    findings: list[str] = []
    for declaration in _php_function_declarations_from_tokens(text, tokens):
        if not _php_comment_has_purpose(declaration, comments):
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
            text = path.read_text(encoding="utf-8")
            findings.extend(
                check_line_declarations(
                    path,
                    powershell_function_declarations(text),
                    powershell_declaration_has_purpose,
                )
            )
        elif kind == "shell":
            text = path.read_text(encoding="utf-8")
            findings.extend(
                check_line_declarations(
                    path,
                    shell_function_declarations(text),
                    shell_declaration_has_purpose,
                )
            )
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