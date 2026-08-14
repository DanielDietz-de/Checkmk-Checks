#!/usr/bin/env python3
"""Validate GitHub Actions runner selection from parsed workflow YAML.

Ordinary repository CI must run on the privately managed self-hosted Linux
runner farm. A small reviewed exception inventory permits exact GitHub-hosted
images only when the execution environment itself is part of the validation or
trust boundary. Runner selectors are inspected from the YAML syntax tree so
quoted, escaped, anchored, explicit-key, and flow-style spellings cannot bypass
the policy.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

GITHUB_HOSTED_RE = re.compile(
    r"^(?:ubuntu|windows|macos)-(?:latest|slim|[A-Za-z0-9][A-Za-z0-9.-]*)$",
    re.IGNORECASE,
)
EXPRESSION_MARKER = "${{"

# Exact, reviewable exceptions. Do not broaden this mapping merely to make CI pass.
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


def _runner_nodes(node: Node | None) -> list[tuple[int, Node]]:
    """Return every structurally decoded ``runs-on`` value and source line."""

    if node is None:
        return []
    found: list[tuple[int, Node]] = []
    if isinstance(node, MappingNode):
        for key_node, value_node in node.value:
            if isinstance(key_node, ScalarNode) and key_node.value == "runs-on":
                found.append((key_node.start_mark.line + 1, value_node))
            found.extend(_runner_nodes(value_node))
    elif isinstance(node, SequenceNode):
        for child in node.value:
            found.extend(_runner_nodes(child))
    return found


def _scalar(node: Node) -> str | None:
    """Return a scalar node value without interpreting YAML-native types."""

    if not isinstance(node, ScalarNode):
        return None
    return str(node.value).strip()


def _static_labels(node: Node) -> tuple[list[str] | None, str | None]:
    """Return static labels from one supported selector and any structural error."""

    if isinstance(node, ScalarNode):
        value = _scalar(node) or ""
        if EXPRESSION_MARKER in value:
            return None, "dynamic runs-on expressions are not permitted"
        return [value.lower()], None

    if isinstance(node, SequenceNode):
        labels: list[str] = []
        for child in node.value:
            value = _scalar(child)
            if value is None:
                return None, "runs-on label arrays may contain only literal scalars"
            if EXPRESSION_MARKER in value:
                return None, "dynamic runs-on expressions are not permitted"
            labels.append(value.lower())
        return labels, None

    if isinstance(node, MappingNode):
        fields: dict[str, Node] = {}
        for key_node, value_node in node.value:
            key = _scalar(key_node)
            if key is None or key not in {"group", "labels"}:
                return None, "runs-on mappings may contain only group and labels keys"
            if key in fields:
                return None, f"runs-on mapping contains duplicate {key!r} keys"
            fields[key] = value_node
        if "labels" not in fields:
            return None, "ordinary runs-on mappings must include explicit labels"
        if "group" in fields:
            group = _scalar(fields["group"])
            if group is None or EXPRESSION_MARKER in group:
                return None, "runs-on group must be one static literal scalar"
        labels_node = fields["labels"]
        if isinstance(labels_node, ScalarNode):
            value = _scalar(labels_node) or ""
            if EXPRESSION_MARKER in value:
                return None, "dynamic runs-on expressions are not permitted"
            return [value.lower()], None
        if isinstance(labels_node, SequenceNode):
            labels = []
            for child in labels_node.value:
                value = _scalar(child)
                if value is None:
                    return None, "runs-on labels may contain only literal scalars"
                if EXPRESSION_MARKER in value:
                    return None, "dynamic runs-on expressions are not permitted"
                labels.append(value.lower())
            return labels, None
        return None, "runs-on labels must be a literal scalar or sequence"

    return None, "unsupported runs-on selector structure"


def _validate_selector(relative: str, line: int, node: Node) -> tuple[list[str], bool]:
    """Validate one parsed runner selector and report exception use."""

    errors: list[str] = []
    allowed = GITHUB_HOSTED_EXCEPTIONS.get(relative)

    # Hosted exceptions must be one exact scalar. Arrays/mappings are deliberately
    # not accepted for exception workflows because they can broaden routing.
    scalar = _scalar(node)
    if scalar is not None and EXPRESSION_MARKER not in scalar:
        normalized = scalar.lower()
        if allowed and normalized in allowed:
            return [], True

    labels, structure_error = _static_labels(node)
    if structure_error:
        errors.append(f"{relative}:{line}: {structure_error}")
        return errors, False
    assert labels is not None

    hosted = sorted({label for label in labels if GITHUB_HOSTED_RE.fullmatch(label)})
    for label in hosted:
        errors.append(
            f"{relative}:{line}: GitHub-hosted runner label {label!r} "
            "is not an approved exact exception"
        )
    if hosted:
        return errors, False

    # A single scalar is one GitHub runner label, not a space/comma separated list.
    # Requiring both labels therefore naturally forces an array or labels mapping.
    missing = [label for label in ("self-hosted", "linux") if label not in labels]
    if missing:
        errors.append(
            f"{relative}:{line}: ordinary runs-on must explicitly include both "
            f"self-hosted and linux labels; missing {', '.join(missing)}"
        )
    return errors, False


def validate_workflow_runners(root: Path) -> list[str]:
    """Return runner-policy violations for all structurally parsed workflows."""

    errors: list[str] = []
    seen_exception_workflows: set[str] = set()

    for path in workflow_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{relative}: cannot read workflow: {exc}")
            continue
        try:
            document = yaml.compose(text, Loader=yaml.SafeLoader)
        except yaml.YAMLError as exc:
            errors.append(f"{relative}: invalid YAML: {exc}")
            continue

        selectors = _runner_nodes(document)
        for line, node in selectors:
            selector_errors, used_exception = _validate_selector(relative, line, node)
            errors.extend(selector_errors)
            if used_exception:
                seen_exception_workflows.add(relative)

    present = {path.relative_to(root).as_posix() for path in workflow_files(root)}
    for relative in sorted(set(GITHUB_HOSTED_EXCEPTIONS) & present):
        if relative not in seen_exception_workflows:
            errors.append(
                f"{relative}: configured GitHub-hosted exception was not matched by "
                "an exact approved scalar runner label"
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
        "Validated structural self-hosted Linux runner policy with "
        f"{len(GITHUB_HOSTED_EXCEPTIONS)} pinned hosted exceptions "
        f"across {len(workflow_files(root))} workflows."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
