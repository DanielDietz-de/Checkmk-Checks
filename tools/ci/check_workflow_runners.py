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
SELF_HOSTED_RE = re.compile(r"(?<![A-Za-z0-9_-])self-hosted(?![A-Za-z0-9_-])", re.IGNORECASE)
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


def _runs_on_blocks(text: str) -> list[tuple[int, str]]:
    """Return line numbers and complete inline or indented ``runs-on`` blocks."""

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
        parts = [match.group("value")]
        index += 1
        while index < len(lines):
            candidate = lines[index]
            if not candidate.strip() or candidate.lstrip().startswith("#"):
                index += 1
                continue
            candidate_indent = len(candidate) - len(candidate.lstrip())
            if candidate_indent <= indent:
                break
            parts.append(candidate.strip())
            index += 1
        blocks.append((line_number, " ".join(parts)))
    return blocks


def _hosted_labels(block: str) -> list[str]:
    """Return normalized GitHub-hosted labels referenced by one runner selector."""

    return [match.group(0).lower() for match in GITHUB_HOSTED_RE.finditer(block)]


def _is_allowed_hosted_exception(relative: str, labels: list[str], block: str) -> bool:
    """Return whether one runner selector exactly matches a pinned hosted exception."""

    allowed = GITHUB_HOSTED_EXCEPTIONS.get(relative)
    if allowed is None:
        return False
    if SELF_HOSTED_RE.search(block):
        return False
    return bool(labels) and set(labels).issubset(allowed)


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

        for line_number, block in _runs_on_blocks(text):
            labels = _hosted_labels(block)
            if labels:
                if _is_allowed_hosted_exception(relative, labels, block):
                    seen_exception_workflows.add(relative)
                    continue
                for hosted in labels:
                    errors.append(
                        f"{relative}:{line_number}: GitHub-hosted runner label "
                        f"{hosted!r} is not an approved exception"
                    )
                if SELF_HOSTED_RE.search(block):
                    errors.append(
                        f"{relative}:{line_number}: hosted and self-hosted labels "
                        "must not be mixed"
                    )
                continue

            if not SELF_HOSTED_RE.search(block):
                errors.append(
                    f"{relative}:{line_number}: runs-on must explicitly include "
                    "the self-hosted label"
                )

    # A configured exception must remain exact if that workflow is present. This catches
    # a workflow silently switching to a dynamic or otherwise unrecognized selector.
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
        "Validated self-hosted runner policy with "
        f"{len(GITHUB_HOSTED_EXCEPTIONS)} pinned hosted exceptions "
        f"across {len(workflow_files(root))} workflows."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
