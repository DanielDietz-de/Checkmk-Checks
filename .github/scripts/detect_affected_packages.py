#!/usr/bin/env python3
"""Select the minimum safe Checkmk package validation scope for a change set."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Literal

Mode = Literal["none", "targeted", "full"]

_SHARED_EXACT = {
    ".github/repository-mkp-release.json",
    "create_mkp_index.py",
    "mkp_index.json",
    "update_readmes.py",
}
_SHARED_PREFIXES = (
    ".github/scripts/",
    ".github/tests/",
    ".github/workflows/",
    "tools/ci/",
    "tests/",
)
_DOC_EXACT = {
    ".gitignore",
    ".github/pull_request_template.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "MAINTENANCE.md",
    "README.md",
    "SECURITY.md",
    "SUPPORT.md",
}
_DOC_PREFIXES = ("docs/", ".github/ISSUE_TEMPLATE/")
_PACKAGE_MANIFEST_PATHS = {"src/info", "src/info.json"}


@dataclass(frozen=True)
class Change:
    status: str
    paths: tuple[str, ...]


@dataclass(frozen=True)
class Selection:
    mode: Mode
    packages: tuple[str, ...]
    reason: str

    def as_json(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "packages": list(self.packages),
            "reason": self.reason,
        }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--event-name", default="pull_request")
    parser.add_argument("--ref", default="")
    parser.add_argument("--github-output", type=Path)
    return parser.parse_args()


def discover_packages(repository: Path) -> set[str]:
    """Return active package directories from canonical manifests only."""
    return {
        path.parent.parent.name
        for path in repository.glob("*/src/info")
        if path.is_file()
    }


def _safe_path(value: str) -> bool:
    path = PurePosixPath(value)
    return (
        bool(value)
        and "\r" not in value
        and "\n" not in value
        and not path.is_absolute()
        and ".." not in path.parts
    )


def parse_name_status(data: bytes) -> list[Change]:
    """Parse ``git diff --name-status -z`` output without shell splitting."""
    fields = data.decode("utf-8", errors="strict").split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    changes: list[Change] = []
    index = 0
    while index < len(fields):
        status = fields[index]
        index += 1
        path_count = 2 if status[:1] in {"R", "C"} else 1
        if index + path_count > len(fields):
            raise ValueError("truncated git name-status output")
        paths = tuple(fields[index : index + path_count])
        index += path_count
        changes.append(Change(status=status, paths=paths))
    return changes


def git_changes(repository: Path, base: str, head: str) -> list[Change]:
    if not base or set(base) == {"0"}:
        raise ValueError("comparison base is unavailable")
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-status",
            "-z",
            "--find-renames",
            base,
            head,
        ],
        cwd=repository,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return parse_name_status(result.stdout)


def classify_changes(
    repository: Path,
    changes: Iterable[Change],
    *,
    force_full_reason: str | None = None,
) -> Selection:
    """Classify changes, defaulting to full validation whenever scope is unclear."""
    if force_full_reason:
        return Selection("full", (), force_full_reason)

    packages = discover_packages(repository)
    targeted: set[str] = set()
    saw_change = False

    for change in changes:
        saw_change = True
        status_type = change.status[:1]
        if status_type not in {"A", "M", "T"}:
            return Selection(
                "full",
                (),
                f"{change.status} change requires repository-wide validation",
            )

        for raw_path in change.paths:
            if not _safe_path(raw_path):
                return Selection("full", (), f"unsafe or ambiguous path: {raw_path!r}")
            path = PurePosixPath(raw_path)
            rendered = path.as_posix()

            if rendered in _SHARED_EXACT or rendered.startswith(_SHARED_PREFIXES):
                return Selection("full", (), f"shared validation input changed: {rendered}")

            if rendered in _DOC_EXACT or rendered.startswith(_DOC_PREFIXES):
                continue

            top = path.parts[0]
            if top not in packages:
                return Selection("full", (), f"unmapped repository path changed: {rendered}")

            relative = PurePosixPath(*path.parts[1:])
            relative_text = relative.as_posix()
            if relative_text == "README.md":
                continue
            if relative_text in _PACKAGE_MANIFEST_PATHS:
                return Selection(
                    "full",
                    (),
                    f"canonical package metadata changed: {rendered}",
                )
            if relative.parts and relative.parts[0] in {"src", "tests"}:
                targeted.add(top)
                continue
            if rendered.endswith((".mkp", ".mkp.sha256")):
                return Selection("full", (), f"generated package artifact changed: {rendered}")
            return Selection("full", (), f"ambiguous package path changed: {rendered}")

    if targeted:
        selected = tuple(sorted(targeted))
        return Selection(
            "targeted",
            selected,
            f"package-local changes affect {', '.join(selected)}",
        )
    if saw_change:
        return Selection("none", (), "documentation-only change")
    return Selection("none", (), "no changed files")


def select_for_event(
    repository: Path,
    *,
    event_name: str,
    ref: str,
    base: str,
    head: str,
) -> Selection:
    if event_name != "pull_request":
        return Selection(
            "full",
            (),
            f"{event_name} event on {ref or 'unknown ref'} requires full validation",
        )
    try:
        changes = git_changes(repository, base, head)
    except (OSError, subprocess.CalledProcessError, UnicodeError, ValueError) as exc:
        return Selection("full", (), f"unable to determine a safe diff: {exc}")
    return classify_changes(repository, changes)


def _single_line(value: str) -> str:
    """Encode control separators before writing GitHub's line-based output file."""
    return value.replace("\r", "\\r").replace("\n", "\\n")


def _write_github_output(path: Path, selection: Selection) -> None:
    packages_json = json.dumps(list(selection.packages), separators=(",", ":"))
    values = {
        "mode": selection.mode,
        "packages": packages_json,
        "package-count": str(len(selection.packages)),
        "reason": selection.reason,
    }
    with path.open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={_single_line(value)}\n")


def main() -> None:
    args = _parse_args()
    repository = args.repository.resolve()
    selection = select_for_event(
        repository,
        event_name=args.event_name,
        ref=args.ref,
        base=args.base,
        head=args.head,
    )
    print(json.dumps(selection.as_json(), indent=2, sort_keys=True))
    output = args.github_output
    if output is None and os.environ.get("GITHUB_OUTPUT"):
        output = Path(os.environ["GITHUB_OUTPUT"])
    if output is not None:
        _write_github_output(output, selection)


if __name__ == "__main__":
    main()
