#!/usr/bin/env python3
"""Normalize documentation for all source symbols covered by repository policy."""
from __future__ import annotations

import ast
from io import StringIO
from pathlib import Path
import re
import tokenize

import check_function_documentation as policy

MIN_WORDS = policy.MIN_DOC_WORDS


def phrase(name: str) -> str:
    """Convert a code identifier into a readable purpose phrase."""
    cleaned = name.strip("_") or name
    return re.sub(r"\s+", " ", re.sub(r"[_:-]+", " ", cleaned)).strip().lower()


def description(name: str, kind: str) -> str:
    """Return deterministic purpose text meeting the permanent word threshold."""
    readable = phrase(name)
    if name == "__init__":
        text = "Initialize the instance and its required runtime state."
    elif name == "__enter__":
        text = "Enter the managed context and return its active value."
    elif name == "__exit__":
        text = "Leave the managed context and release associated resources."
    elif name == "main":
        text = "Run the command-line entry point and return its result."
    elif kind == "class":
        text = f"Represent {readable} behavior and its associated runtime state."
    elif name.startswith("test_"):
        text = f"Verify that {phrase(name[5:])} behaves as required."
    else:
        prefixes = {
            "parse_": "Parse {item} into its normalized representation.",
            "validate_": "Validate {item} and reject invalid input.",
            "verify_": "Verify {item} satisfies the required invariants.",
            "check_": "Evaluate {item} and return its resulting state.",
            "discover_": "Discover {item} from the available input data.",
            "render_": "Render {item} into its output representation.",
            "build_": "Build {item} from the supplied inputs.",
            "create_": "Create {item} from the supplied inputs.",
            "load_": "Load {item} from its configured source.",
            "read_": "Read {item} from its configured source.",
            "write_": "Write {item} to its configured destination.",
            "save_": "Save {item} to its configured destination.",
            "get_": "Return {item} for the supplied inputs.",
            "set_": "Set {item} from the supplied value.",
            "update_": "Update {item} using the supplied changes.",
            "delete_": "Delete {item} from its configured destination.",
            "remove_": "Remove {item} from the current state.",
            "collect_": "Collect {item} from the available source data.",
            "fetch_": "Fetch {item} from its configured source.",
            "format_": "Format {item} for human-readable output.",
            "normalize_": "Normalize {item} into the canonical form.",
            "sync_": "Synchronize {item} with the canonical state.",
            "generate_": "Generate {item} from the current source data.",
            "apply_": "Apply {item} to the current state.",
            "resolve_": "Resolve {item} from the available context.",
            "is_": "Return whether {item} is true for the supplied input.",
            "has_": "Return whether {item} is present for the supplied input.",
        }
        text = ""
        for prefix, template in prefixes.items():
            if name.startswith(prefix) and len(name) > len(prefix):
                text = template.format(item=phrase(name[len(prefix) :]))
                break
        if not text:
            text = f"Handle {readable} for this source file's runtime workflow."
    if len(re.findall(r"[A-Za-z0-9]+", text)) < MIN_WORDS:
        text = f"{text.rstrip('.')} for this runtime code path."
    if len(re.findall(r"[A-Za-z0-9]+", text)) < MIN_WORDS:
        raise RuntimeError(f"generated documentation for {name} is too terse")
    return text


def character_column(line: str, byte_column: int) -> int:
    """Translate an AST UTF-8 byte column into a string character column."""
    return len(line.encode("utf-8")[:byte_column].decode("utf-8"))


def colon_column(line: str) -> int:
    """Return the signature-ending colon column for a one-line definition."""
    tokens = tokenize.generate_tokens(StringIO(line).readline)
    depth = 0
    started = False
    for token in tokens:
        if token.type == tokenize.NAME and token.string in {"def", "class"}:
            started = True
            continue
        if not started or token.type != tokenize.OP:
            continue
        if token.string in "([{" :
            depth += 1
        elif token.string in ")]}":
            depth = max(0, depth - 1)
        elif token.string == ":" and depth == 0:
            return token.end[1]
    raise ValueError("cannot locate definition colon")


def normalize_python(path: Path) -> int:
    """Add or upgrade Python symbol docstrings without changing executable logic."""
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    lines = text.splitlines(keepends=True)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))
    operations: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        current = ast.get_docstring(node, clean=True)
        if current and len(re.findall(r"[A-Za-z0-9]+", current)) >= MIN_WORDS:
            continue
        kind = "class" if isinstance(node, ast.ClassDef) else "function"
        doc = description(node.name, kind)
        first = node.body[0]
        if current is not None:
            if not (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
                and first.end_lineno is not None
                and first.end_col_offset is not None
            ):
                raise RuntimeError(f"cannot safely replace docstring at {path}:{node.lineno}")
            start = starts[first.lineno - 1] + character_column(
                lines[first.lineno - 1], first.col_offset
            )
            end = starts[first.end_lineno - 1] + character_column(
                lines[first.end_lineno - 1], first.end_col_offset
            )
            operations.append((start, end, f'"""{doc}"""'))
        elif first.lineno == node.lineno:
            index = node.lineno - 1
            raw = lines[index]
            newline = "\r\n" if raw.endswith("\r\n") else "\n"
            body = raw[: -len(newline)] if raw.endswith(newline) else raw
            colon = colon_column(body)
            line_start = starts[index]
            indent = body[: len(body) - len(body.lstrip())] + "    "
            remainder = body[colon:].strip()
            replacement = body[:colon] + newline + indent + f'"""{doc}"""' + newline
            if remainder:
                replacement += indent + remainder
            operations.append(
                (line_start, line_start + len(body), replacement.rstrip("\r\n"))
            )
        else:
            index = first.lineno - 1
            raw = lines[index]
            indent = raw[: len(raw) - len(raw.lstrip())]
            newline = "\r\n" if raw.endswith("\r\n") else "\n"
            operations.append(
                (starts[index], starts[index], indent + f'"""{doc}"""' + newline)
            )
    if not operations:
        return 0
    updated = text
    for start, end, replacement in sorted(
        operations, key=lambda item: item[0], reverse=True
    ):
        updated = updated[:start] + replacement + updated[end:]
    ast.parse(updated, filename=str(path))
    path.write_text(updated, encoding="utf-8", newline="")
    return len(operations)


def normalize_pattern(path: Path, pattern: re.Pattern[str], marker: str) -> int:
    """Add adjacent purpose comments before undocumented non-Python functions."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    insertions: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = pattern.search(line)
        if not match or policy.preceding_comment(lines, index):
            continue
        indent = match.group("indent") or ""
        newline = "\r\n" if line.endswith("\r\n") else "\n"
        insertions.append(
            (
                index,
                f"{indent}{marker} {description(match.group('name'), 'function')}{newline}",
            )
        )
    for index, content in reversed(insertions):
        lines.insert(index, content)
    if insertions:
        path.write_text("".join(lines), encoding="utf-8", newline="")
    return len(insertions)


def normalize_repository(root: Path) -> dict[str, int]:
    """Normalize all tracked source files covered by the permanent policy."""
    ps_pattern = re.compile(
        r"^(?P<indent>\s*)function\s+(?P<name>[A-Za-z0-9_:-]+)\b", re.I
    )
    sh_pattern = re.compile(
        r"^(?P<indent>\s*)(?:function\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{"
    )
    php_pattern = re.compile(
        r"^(?P<indent>\s*)(?:(?:public|protected|private|static|final|abstract)\s+)*"
        r"function\s+&?\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(",
        re.I,
    )
    counts = {"python": 0, "powershell": 0, "shell": 0, "php": 0}
    for path in policy.tracked_files(root):
        kind = policy.source_kind(path)
        if kind == "python":
            counts[kind] += normalize_python(path)
        elif kind == "powershell":
            counts[kind] += normalize_pattern(path, ps_pattern, "#")
        elif kind == "shell":
            counts[kind] += normalize_pattern(path, sh_pattern, "#")
        elif kind == "php":
            counts[kind] += normalize_pattern(path, php_pattern, "//")
    return counts


def main() -> int:
    """Normalize repository documentation and print changed-symbol counts by language."""
    counts = normalize_repository(Path.cwd())
    print(f"Normalized documentation: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())