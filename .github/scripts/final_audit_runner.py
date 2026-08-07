#!/usr/bin/env python3
"""Publish the checksum-pinned final repository audit tree.

This temporary bootstrap runs only from the trusted default branch. It treats
PR #38's staging branch as untrusted transport: every accepted path, decoded
archive, patch, byte count, and resulting repository file is verified before
code from the reconstructed tree is executed. Publication uses
force-with-lease against the exact reviewed staging SHA.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

REPOSITORY = "DanielDietz-de/Checkmk-Checks"
BRANCH = "agent/final-repository-completion-audit"
EXPECTED_PREVIOUS_MASTER = "0c4189e1cf2af6e1765454768ca888b5e45ff762"
EXPECTED_MASTER_PATHS = (".github/scripts/final_audit_runner.py",)
EXPECTED_AUDIT_BASE = "ff1129c75c59f79ebec3d1fb61506a5d76c9ca4b"
EXPECTED_STAGING_SHA = "a63b0b2b0b495d316eb506c47cd514f627e746e2"
EXPECTED_GZIP_SHA256 = "a474d18b5cf6084fe4dbb8b1bfe90472ca6cba2dc0a9d717734c3629b37717cc"
EXPECTED_PATCH_SHA256 = "0a02b2c64eaed2c00dac46db6b72c5156216afbd50b4224bee8ee7648c04f9f0"
EXPECTED_PATCH_FILES = 204
EXPECTED_ADDITIONS_XZ_SHA256 = "9c2f00b5c45dfe747a7873da56709f2cb7c0c7724b86c7e77db4a5e6c49e65cb"
EXPECTED_FILES = 1667
EXPECTED_MANIFEST_SHA256 = "d84a25b3b61e63ff5ab13c86bf1d78375b7fd5ced4183282a5dbf16096800cd4"

EXCLUDED_MANIFEST_PARTS = {".git", ".pytest_cache", "__pycache__"}
ALLOWED_STAGING_ROOTS = (
    ".github/final-audit-patch/",
    ".github/final-audit-payload/",
    ".github/final-audit-additions/",
)
ALLOWED_STAGING_FILE = ".github/workflows/apply-final-repository-audit.yml"
TEMPORARY_PATHS = (
    ".github/final-audit-patch",
    ".github/final-audit-payload",
    ".github/final-audit-additions",
    ".github/final-audit-trigger",
    ".github/scripts/final_audit_runner.py",
    ".github/workflows/apply-final-repository-audit.yml",
    ".github/workflows/final-audit-orchestrator.yml",
    ".github/workflows/final-audit-runner.yml",
)


def run(
    *args: str,
    cwd: Path,
    capture: bool = False,
    input_text: str | None = None,
) -> str:
    """Run one bounded command and optionally return its stripped stdout."""

    completed = subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        input=input_text,
        stdout=subprocess.PIPE if capture else None,
    )
    return completed.stdout.strip() if capture and completed.stdout else ""


def require(condition: bool, message: str) -> None:
    """Abort the audit transaction when a required invariant is false."""

    if not condition:
        raise RuntimeError(message)


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase SHA-256 digest for ``data``."""

    return hashlib.sha256(data).hexdigest()


def require_digest(data: bytes, expected: str, label: str) -> None:
    """Require ``data`` to match a pinned digest and report both values."""

    actual = sha256_bytes(data)
    require(
        actual == expected,
        f"{label} digest mismatch: actual={actual} expected={expected}",
    )


def decode_base64_transport(data: bytes, label: str) -> bytes:
    """Decode base64 after removing transport-only ASCII whitespace.

    Line wrapping and trailing newlines are not security-relevant. The decoded
    binary is authenticated independently by a pinned SHA-256 digest.
    """

    canonical = b"".join(data.split())
    require(bool(canonical), f"{label} base64 transport is empty")
    try:
        return base64.b64decode(canonical, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RuntimeError(f"{label} base64 transport is invalid: {exc}") from exc


def verify_master_state(repository: Path) -> str:
    """Verify that the bootstrap merge is the sole change after trusted master."""

    run("git", "fetch", "--no-tags", "origin", "master", cwd=repository)
    master_sha = run("git", "rev-parse", "origin/master", cwd=repository, capture=True)
    first_parent = run(
        "git", "rev-parse", "origin/master^1", cwd=repository, capture=True
    )
    require(
        first_parent == EXPECTED_PREVIOUS_MASTER,
        f"master first parent {first_parent} is not {EXPECTED_PREVIOUS_MASTER}",
    )
    changed = run(
        "git",
        "diff",
        "--name-only",
        EXPECTED_PREVIOUS_MASTER,
        master_sha,
        cwd=repository,
        capture=True,
    ).splitlines()
    require(
        tuple(sorted(changed)) == tuple(sorted(EXPECTED_MASTER_PATHS)),
        f"unexpected master bootstrap paths: {changed}",
    )
    return master_sha


def verify_staging_state(repository: Path) -> None:
    """Verify the exact staging commit and its strictly allowlisted path set."""

    actual = run("git", "rev-parse", "HEAD", cwd=repository, capture=True)
    require(actual == EXPECTED_STAGING_SHA, f"staging SHA moved to {actual}")
    changed = run(
        "git",
        "diff",
        "--name-only",
        EXPECTED_AUDIT_BASE,
        "HEAD",
        cwd=repository,
        capture=True,
    ).splitlines()
    for raw in changed:
        path = PurePosixPath(raw)
        require(not path.is_absolute(), f"absolute staging path: {raw!r}")
        require(".." not in path.parts, f"traversal staging path: {raw!r}")
        allowed = raw == ALLOWED_STAGING_FILE or raw.startswith(ALLOWED_STAGING_ROOTS)
        require(allowed, f"unexpected staging path: {raw!r}")


def decode_audit_patch(repository: Path) -> bytes:
    """Reassemble, decode, authenticate, decompress, and validate the patch."""

    chunks = sorted((repository / ".github/final-audit-patch").glob("chunk*.b64"))
    require(len(chunks) == 9, f"expected 9 patch chunks, found {len(chunks)}")
    encoded = b"".join(path.read_bytes() for path in chunks)
    compressed = decode_base64_transport(encoded, "audit patch")
    require_digest(compressed, EXPECTED_GZIP_SHA256, "audit patch gzip")
    patch = gzip.decompress(compressed)
    require_digest(patch, EXPECTED_PATCH_SHA256, "audit patch")
    validate_patch_paths(patch)
    return patch


def validate_patch_paths(patch: bytes) -> None:
    """Validate every destination path declared by the unified audit patch."""

    text = patch.decode("utf-8")
    paths: list[str] = []
    for line in text.splitlines():
        if not line.startswith("+++ source/"):
            continue
        raw = line.split("\t", 1)[0][len("+++ source/") :]
        path = PurePosixPath(raw)
        require(not path.is_absolute(), f"absolute patch path: {raw!r}")
        require(".." not in path.parts, f"traversal patch path: {raw!r}")
        require(
            not raw.startswith(".github/final-audit-"),
            f"patch contains staging path: {raw!r}",
        )
        require(
            not raw.startswith(".github/workflows/final-audit-"),
            f"patch contains orchestrator path: {raw!r}",
        )
        paths.append(raw)
    require(
        len(paths) == EXPECTED_PATCH_FILES and len(set(paths)) == EXPECTED_PATCH_FILES,
        (
            f"expected {EXPECTED_PATCH_FILES} unique patch paths; "
            f"got {len(paths)} entries and {len(set(paths))} unique paths"
        ),
    )


def extract_additions(repository: Path, destination: Path) -> None:
    """Decode, authenticate, and safely extract documentation additions."""

    encoded = (repository / ".github/final-audit-additions/additions.b64").read_bytes()
    archive_bytes = decode_base64_transport(encoded, "additions archive")
    require_digest(archive_bytes, EXPECTED_ADDITIONS_XZ_SHA256, "additions xz")
    total = 0
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:xz") as archive:
        members = archive.getmembers()
        for member in members:
            path = PurePosixPath(member.name)
            require(not path.is_absolute(), f"absolute archive path: {member.name!r}")
            require(".." not in path.parts, f"traversal archive path: {member.name!r}")
            allowed = member.name in {"runtime", "payload"} or member.name.startswith(
                ("runtime/", "payload/")
            )
            require(allowed, f"unexpected archive member: {member.name!r}")
            require(
                not (member.issym() or member.islnk() or member.isdev()),
                f"unsupported archive member type: {member.name!r}",
            )
            total += member.size
        require(total <= 250_000, f"additions archive exceeds size bound: {total}")
        archive.extractall(destination, members=members, filter="data")


def remove_temporary_paths(repository: Path) -> None:
    """Remove every payload, trigger, orchestrator, and runner bootstrap path."""

    for relative in TEMPORARY_PATHS:
        path = repository / relative
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()


def reconstruct_tree(repository: Path, patch: bytes, additions: Path) -> None:
    """Apply the authenticated patch and full-tree documentation additions."""

    subprocess.run(
        ["patch", "--strip=1", "--batch", "--forward"],
        cwd=repository,
        check=True,
        input=patch,
    )
    shutil.rmtree(repository / ".github/final-audit-patch")
    shutil.rmtree(repository / ".github/final-audit-payload")
    (repository / ALLOWED_STAGING_FILE).unlink(missing_ok=True)

    documenter = additions / "runtime/document_symbols.py"
    require(documenter.is_file(), "documentation generator is missing")
    run(sys.executable, str(documenter), cwd=repository)
    payload = additions / "payload"
    require(payload.is_dir(), "additions payload directory is missing")
    shutil.copytree(payload, repository, dirs_exist_ok=True, copy_function=shutil.copy2)

    run(sys.executable, "tools/ci/sync_package_metadata.py", "--write", cwd=repository)
    run(sys.executable, "tools/ci/generate_package_reference.py", "--write", cwd=repository)
    remove_temporary_paths(repository)


def manifest(repository: Path) -> tuple[int, str]:
    """Return the canonical file count and SHA-256 manifest digest."""

    entries: list[str] = []
    for path in sorted(repository.rglob("*")):
        relative = path.relative_to(repository)
        if any(part in EXCLUDED_MANIFEST_PARTS for part in relative.parts):
            continue
        if not path.is_file():
            continue
        mode = "755" if path.stat().st_mode & stat.S_IXUSR else "644"
        digest = sha256_bytes(path.read_bytes())
        entries.append(f"{mode} {digest} {relative.as_posix()}")
    encoded = ("\n".join(entries) + "\n").encode()
    return len(entries), sha256_bytes(encoded)


def verify_manifest(repository: Path) -> None:
    """Require an exact byte-and-mode match with the reviewed final tree."""

    count, digest = manifest(repository)
    require(
        count == EXPECTED_FILES and digest == EXPECTED_MANIFEST_SHA256,
        (
            f"source manifest mismatch: files={count} sha256={digest}; "
            f"expected files={EXPECTED_FILES} sha256={EXPECTED_MANIFEST_SHA256}"
        ),
    )
    print(f"Verified exact source manifest: {count} files, sha256={digest}")


def validate_tree(repository: Path, temporary: Path) -> None:
    """Run the complete security, documentation, test, and MKP build suite."""

    commands = (
        (sys.executable, "tools/ci/pin_supply_chain.py", "--check"),
        (sys.executable, "tools/ci/normalize_package_sources.py"),
        (sys.executable, "tools/ci/check_package_collisions.py"),
        (sys.executable, "tools/ci/check_repository_quality.py"),
        (sys.executable, "tools/ci/sync_repository_facts.py"),
        (sys.executable, "tools/ci/sync_package_metadata.py"),
        (sys.executable, "tools/ci/generate_package_reference.py"),
        (sys.executable, "tools/ci/manage_module_docstrings.py"),
        (sys.executable, "tools/ci/check_python_syntax.py"),
    )
    for command in commands:
        run(*command, cwd=repository)
    run(
        sys.executable,
        "tools/ci/full_repository_audit.py",
        "--fail-on",
        "low",
        "--output",
        str(temporary / "repository-audit.json"),
        cwd=repository,
    )
    run(
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-p",
        "test_ci_*.py",
        "-v",
        cwd=repository,
    )
    run(sys.executable, "-m", "pytest", "-q", ".github/tests", cwd=repository)
    package_tests = [str(path) for path in sorted(repository.glob("*/tests"))]
    require(package_tests, "no package test directories were discovered")
    run(sys.executable, "-m", "pytest", "-q", *package_tests, cwd=repository)
    run(
        sys.executable,
        ".github/scripts/build_repository_mkps.py",
        "--repository",
        ".",
        "--output",
        str(temporary / "repository-mkps"),
        "--packaged-version",
        "2.5.0p9",
        cwd=repository,
    )
    run("git", "diff", "--check", cwd=repository)


def publish(repository: Path, master_sha: str) -> str:
    """Create one clean commit and replace the staging branch with lease safety."""

    run("git", "config", "user.name", "github-actions[bot]", cwd=repository)
    run(
        "git",
        "config",
        "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
        cwd=repository,
    )
    run("git", "add", "--all", cwd=repository)
    tree = run("git", "write-tree", cwd=repository, capture=True)
    commit = run(
        "git",
        "commit-tree",
        tree,
        "-p",
        master_sha,
        cwd=repository,
        capture=True,
        input_text="audit: complete repository validation and hardening\n",
    )
    run(
        "git",
        "push",
        f"--force-with-lease=refs/heads/{BRANCH}:{EXPECTED_STAGING_SHA}",
        "origin",
        f"{commit}:refs/heads/{BRANCH}",
        cwd=repository,
    )
    print(f"Published clean audit commit {commit}")
    return commit


def dispatch_workflows(token: str) -> None:
    """Dispatch both authoritative workflows against the rewritten branch."""

    require(bool(token), "GITHUB_TOKEN is required for workflow dispatch")
    data = json.dumps({"ref": BRANCH}).encode()
    for workflow in ("repository-guard.yml", "repository-mkp-ci.yml"):
        request = urllib.request.Request(
            (
                f"https://api.github.com/repos/{REPOSITORY}/actions/workflows/"
                f"{workflow}/dispatches"
            ),
            data=data,
            method="POST",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            require(response.status == 204, f"workflow dispatch failed: {workflow}")


def parse_args() -> argparse.Namespace:
    """Parse the staging repository path supplied by the workflow."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    """Execute the fail-closed reconstruction, validation, and publication flow."""

    args = parse_args()
    repository = args.repository.resolve()
    require((repository / ".git").exists(), f"not a Git repository: {repository}")
    master_sha = verify_master_state(repository)
    verify_staging_state(repository)
    patch = decode_audit_patch(repository)
    with tempfile.TemporaryDirectory(prefix="final-audit-") as temporary_name:
        temporary = Path(temporary_name)
        additions = temporary / "additions"
        additions.mkdir()
        extract_additions(repository, additions)
        reconstruct_tree(repository, patch, additions)
        verify_manifest(repository)
        validate_tree(repository, temporary)
    publish(repository, master_sha)
    dispatch_workflows(os.environ.get("GITHUB_TOKEN", ""))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - fail closed with an actionable log.
        print(f"final audit runner failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
