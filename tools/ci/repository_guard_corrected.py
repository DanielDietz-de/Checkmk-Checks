#!/usr/bin/env python3
"""Repository-wide guardrails for changed Checkmk extension code.

Existing legacy debt is inventoried rather than converted into an immediate
repository-wide failure. A package becomes subject to the stricter baseline as
soon as its source or metadata is changed.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

BANNED_TEXT = {
    ".unsafe(": "Checkmk Secret values must not be flattened",
    "shell=True": "subprocess shell execution is prohibited",
    "shell = True": "subprocess shell execution is prohibited",
    "urllib3.disable_warnings": "global TLS warning suppression is prohibited",
    "requests.packages.urllib3.disable_warnings": "global TLS warning suppression is prohibited",
}
SOURCE_SUFFIXES = {".py", ".sh", ".bash", ".php", ".rb"}
METADATA_NAMES = {"info", "info.json"}


class GuardError(RuntimeError):
    """Raised when repository state cannot be inspected reliably."""


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise GuardError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def changed_files(root: Path, base: str | None, head: str | None) -> list[Path]:
    if base and head and set(base) != {"0"}:
        output = git_output(root, "diff", "--name-only", "--diff-filter=ACMR", base, head)
    else:
        output = git_output(root, "show", "--pretty=format:", "--name-only", "HEAD")
    return [root / line for line in output.splitlines() if line.strip()]


def package_for(root: Path, path: Path) -> Path | None:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return None
    if len(relative.parts) < 2:
        return None
    candidate = root / relative.parts[0]
    if (candidate / "src" / "info").is_file() or (candidate / "src" / "info.json").is_file():
        return candidate
    return None


def changed_packages(root: Path, paths: list[Path]) -> set[Path]:
    return {package for path in paths if (package := package_for(root, path)) is not None}


def load_metadata(path: Path) -> dict[str, Any]:
    try:
        if path.name == "info.json":
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = ast.literal_eval(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, SyntaxError, ValueError, TypeError) as exc:
        raise GuardError(f"cannot parse metadata {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise GuardError(f"metadata {path} is not a dictionary/object")
    return data


def validate_metadata(root: Path, touched_packages: set[Path]) -> list[str]:
    """Parse all metadata, but require full consistency only for touched packages."""
    errors: list[str] = []
    for package in sorted(path for path in root.iterdir() if path.is_dir()):
        info = package / "src" / "info"
        info_json = package / "src" / "info.json"
        records: list[tuple[Path, dict[str, Any]]] = []
        for path in (info, info_json):
            if not path.is_file():
                continue
            try:
                records.append((path, load_metadata(path)))
            except GuardError as exc:
                errors.append(str(exc))
        if not records or package not in touched_packages:
            continue
        for path, data in records:
            for key in ("name", "version", "files"):
                if key not in data:
                    errors.append(f"metadata {path} is missing {key}")
            if "files" in data and not isinstance(data["files"], dict):
                errors.append(f"metadata {path} files is not a dictionary")
        if len(records) == 2:
            left_path, left = records[0]
            right_path, right = records[1]
            for key in (
                "name",
                "version",
                "version.min_required",
                "version.packaged",
                "version.usable_until",
            ):
                if left.get(key) != right.get(key):
                    errors.append(
                        f"{package.name}: {key} differs between "
                        f"{left_path.name} and {right_path.name}"
                    )
    return errors


def is_comment_only_match(line: str, token: str) -> bool:
    if token not in line:
        return True
    stripped = line.lstrip()
    return stripped.startswith("#") or stripped.startswith("//")


def validate_changed_source(root: Path, paths: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path.relative_to(root)}: {exc}")
            continue
        if path.suffix == ".py":
            try:
                tree = ast.parse(text, filename=str(path.relative_to(root)))
            except SyntaxError as exc:
                errors.append(f"{path.relative_to(root)}:{exc.lineno}: {exc.msg}")
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
                    errors.append(
                        f"{path.relative_to(root)}:{node.lineno}: builtin eval is prohibited"
                    )
                if isinstance(node, ast.Call):
                    for keyword in node.keywords:
                        if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                            errors.append(
                                f"{path.relative_to(root)}:{node.lineno}: shell=True is prohibited"
                            )
                        if keyword.arg == "verify" and isinstance(keyword.value, ast.Constant) and keyword.value.value is False:
                            errors.append(
                                f"{path.relative_to(root)}:{node.lineno}: verify=False requires an isolated reviewed exception"
                            )
        for number, line in enumerate(text.splitlines(), start=1):
            if "# security-reviewed:" in line:
                continue
            for token, message in BANNED_TEXT.items():
                if token in line and not is_comment_only_match(line, token):
                    errors.append(
                        f"{path.relative_to(root)}:{number}: {message} ({token})"
                    )
    return errors


def validate_changed_packages_have_tests(root: Path, paths: list[Path]) -> list[str]:
    source_packages: set[Path] = set()
    for path in paths:
        package = package_for(root, path)
        if package is None:
            continue
        relative = path.relative_to(package)
        if relative.parts and relative.parts[0] == "src" and path.suffix in SOURCE_SUFFIXES:
            source_packages.add(package)
    errors: list[str] = []
    for package in sorted(source_packages):
        tests = package / "tests"
        if not tests.is_dir() or not any(tests.glob("test_*.py")):
            errors.append(
                f"{package.name}: changed source code requires at least one tests/test_*.py file"
            )
    return errors


def package_inventory(root: Path) -> dict[str, int]:
    total = tested = workflows = legacy = 0
    workflow_dir = root / ".github" / "workflows"
    workflow_paths = [*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")]
    workflow_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(workflow_paths)
    )
    for package in sorted(path for path in root.iterdir() if path.is_dir()):
        metadata_path = package / "src" / "info"
        if not metadata_path.is_file() and not (package / "src" / "info.json").is_file():
            continue
        total += 1
        if (package / "tests").is_dir() and any((package / "tests").glob("test_*.py")):
            tested += 1
        if package.name in workflow_text:
            workflows += 1
        try:
            metadata = load_metadata(
                metadata_path if metadata_path.is_file() else package / "src" / "info.json"
            )
            files = metadata.get("files", {})
            if isinstance(files, dict) and {"agent_based", "checkman", "web", "lib"}.intersection(files):
                legacy += 1
        except GuardError:
            pass
    return {"total": total, "tested": tested, "workflow_referenced": workflows, "legacy_layout": legacy}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--base")
    parser.add_argument("--head")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    try:
        paths = changed_files(root, args.base, args.head)
        touched = changed_packages(root, paths)
        errors = []
        errors.extend(validate_metadata(root, touched))
        errors.extend(validate_changed_source(root, paths))
        errors.extend(validate_changed_packages_have_tests(root, paths))
        inventory = package_inventory(root)
    except GuardError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "changed_files": len(paths),
                "changed_packages": sorted(package.name for package in touched),
                "package_inventory": inventory,
            },
            sort_keys=True,
        )
    )
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
