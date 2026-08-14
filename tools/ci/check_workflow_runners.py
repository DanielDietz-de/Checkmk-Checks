#!/usr/bin/env python3
"""Validate repository workflow runner selection against the explicit execution policy.

Linux CI is expected to run on the privately managed self-hosted runner farm.
A very small set of workflows may use GitHub-hosted runners when their execution
environment is itself part of the validation or trust boundary. Those exceptions
are pinned by exact workflow path and exact runner label so they cannot silently
expand to other workflows or runner images.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

RUNS_ON_RE = re.compile(r"^(?P<indent>\s*)runs-on:\s*(?P<value>.*)$")
UNSUPPORTED_RUNS_ON_KEY_RE = re.compile(
    r"(?:^|[,{?])\s*(?:[\"']runs-on[\"']|runs-on)\s*:",
    re.IGNORECASE,
)
SELF_HOSTED_RE = re.compile(r"(?<![A-Za-z0-9_-])self-hosted(?![A-Za-z0-9_-])", re.IGNORECASE)
LINUX_RE = re.compile(r"(?<![A-Za-z0-9_-])linux(?![A-Za-z0-9_-])", re.IGNORECASE)
GITHUB_HOSTED_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:ubuntu|windows|macos)-(?:latest|slim|[A-Za-z0-9][A-Za-z0-9.-]*)(?![A-Za-z0-9_-])",
    re.IGNORECASE,
)

# Exact, reviewable exceptions. Do not broaden this mapping merely to make CI pass.
# - The final-audit workflows intentionally use ephemeral GitHub-hosted Linux runners
#   as part of their trusted bootstrap boundary.
# - The S2D validation workflow requires Windows PowerShell 5.1 on a Windows runner;
#   the available self-hosted farm is Linux-only.
GITHUB_HOSTED_EXCEPTIONS: dict[str, frozenset[str]] = {
    ".github/workflows/final-audit-orchestrator.yml": frozenset({"ubuntu-24.04"}),
    ".github/workflows/final-audit-runner.yml": frozenset({"ubuntu-24.04"}),
    ".github/workflows/s2d-hci-windows-ci.yml": frozenset({"windows-2025"}),
}


def workflow_files(root: Path) -> list[Path]:
    """Return canonical workflow files in deterministic order."""

    workflow_dir = root / ".github" / "workflows"
    if not workflow_dir.is_dir():
        return []
    return sorted(
        path
        for path in workflow_dir.iterdir()
        if path.is_file() and path.suffix in {".yml", ".yaml"}
    )


def _without_yaml_comment(value: str) -> str:
    """Remove an unquoted YAML comment from the simple runner-selector syntax we allow."""

    # Runner selectors in this repository are deliberately restricted to plain labels,
    # bracket lists, or the documented group/labels mapping. A literal '#' in a quoted
    # runner label is therefore outside the accepted contract and can be treated as a
    # comment delimiter without weakening the policy.
    return value.split("#", 1)[0].strip()


def _runs_on_blocks(text: str) -> list[tuple[int, str]]:
    """Return line numbers and comment-free inline or indented ``runs-on`` blocks."""

    lines = text.splitlines()
    blocks: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        match = RUNS_ON_RE.match(lines[index])
        if not match:
            index += 1
            continue

        line_number = index + 1
        indent = len(match.group("indent"))
        parts = [_without_yaml_comment(match.group("value"))]
        index += 1
        while index < len(lines):
            candidate = lines[index]
            if not candidate.strip() or candidate.lstrip().startswith("#"):
                index += 1
                continue
            candidate_indent = len(candidate) - len(candidate.lstrip())
            if candidate_indent <= indent:
                break
            normalized = _without_yaml_comment(candidate.strip())
            if normalized:
                parts.append(normalized)
            index += 1
        blocks.append((line_number, " ".join(part for part in parts if part)))
    return blocks


def _unsupported_runs_on_lines(text: str) -> list[int]:
    """Find alternate YAML key forms that the restricted selector parser rejects."""

    unsupported: list[int] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if raw_line.lstrip().startswith("#"):
            continue
        line = _without_yaml_comment(raw_line)
        if not line or RUNS_ON_RE.match(line):
            continue
        if UNSUPPORTED_RUNS_ON_KEY_RE.search(line):
            unsupported.append(line_number)
    return unsupported


def _hosted_labels(block: str) -> list[str]:
    """Return normalized GitHub-hosted labels referenced by one runner selector."""

    return [match.group(0).lower() for match in GITHUB_HOSTED_RE.finditer(block)]


def _plain_scalar(block: str) -> str | None:
    """Return one literal scalar selector, rejecting lists, mappings, and expressions."""

    value = block.strip()
    if not value or "${{" in value or value.startswith("[") or ":" in value or " " in value:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value.lower() or None


def _is_allowed_hosted_exception(relative: str, labels: list[str], block: str) -> bool:
    """Return whether the complete selector exactly equals a pinned hosted exception."""

    allowed = GITHUB_HOSTED_EXCEPTIONS.get(relative)
    scalar = _plain_scalar(block)
    if allowed is None or scalar is None:
        return False
    if SELF_HOSTED_RE.search(block):
        return False
    return len(labels) == 1 and labels[0] == scalar and scalar in allowed


def validate_workflow_runners(root: Path) -> list[str]:
    """Return runner-policy violations for all repository workflow selectors."""

    errors: list[str] = []
    seen_exception_workflows: set[str] = set()

    for path in workflow_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{relative}: cannot read workflow: {exc}")
            continue

        for line_number in _unsupported_runs_on_lines(text):
            errors.append(
                f"{relative}:{line_number}: unsupported runs-on key syntax; use the "
                "canonical unquoted block key so runner policy can be verified"
            )

        for line_number, block in _runs_on_blocks(text):
            labels = _hosted_labels(block)
            if labels:
                if _is_allowed_hosted_exception(relative, labels, block):
                    seen_exception_workflows.add(relative)
                    continue
                for hosted in labels:
                    errors.append(
                        f"{relative}:{line_number}: GitHub-hosted runner label "
                        f"{hosted!r} is not an approved exact exception"
                    )
                if SELF_HOSTED_RE.search(block):
                    errors.append(
                        f"{relative}:{line_number}: hosted and self-hosted labels "
                        "must not be mixed"
                    )
                continue

            if "${{" in block:
                errors.append(
                    f"{relative}:{line_number}: dynamic runs-on expressions are not "
                    "permitted by the runner policy"
                )
                continue

            missing: list[str] = []
            if not SELF_HOSTED_RE.search(block):
                missing.append("self-hosted")
            if not LINUX_RE.search(block):
                missing.append("linux")
            if missing:
                errors.append(
                    f"{relative}:{line_number}: ordinary runs-on must explicitly include "
                    f"both self-hosted and linux labels; missing {', '.join(missing)}"
                )

    present = {path.relative_to(root).as_posix() for path in workflow_files(root)}
    for relative in sorted(set(GITHUB_HOSTED_EXCEPTIONS) & present):
        if relative not in seen_exception_workflows:
            errors.append(
                f"{relative}: configured GitHub-hosted exception was not matched by "
                "an exact approved runner label"
            )

    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for repository-root selection."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Validate workflow runner policy and return a process exit status."""

    args = parse_args(argv)
    root = args.root.resolve()
    errors = validate_workflow_runners(root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(
        "Validated self-hosted Linux runner policy with "
        f"{len(GITHUB_HOSTED_EXCEPTIONS)} pinned hosted exceptions "
        f"across {len(workflow_files(root))} workflows."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
