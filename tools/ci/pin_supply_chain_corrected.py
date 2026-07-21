#!/usr/bin/env python3
"""Pin GitHub Actions and Checkmk container images used by workflows.

The tool resolves action tags through the GitHub Git database API and Docker
image tags through the registry manifest API. It writes full commit SHAs and
manifest digests into workflow files and records source tags in a lock file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ACTION_RE = re.compile(
    r"(?P<prefix>\buses:\s*)(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"
    r"@(?P<ref>[^\s#]+)(?P<suffix>\s*(?:#.*)?)$"
)
IMAGE_TAG_RE = re.compile(
    r"(?P<repo>checkmk/check-mk-(?:raw|community)):(?P<tag>[0-9][A-Za-z0-9._-]*)"
)
IMAGE_DIGEST_RE = re.compile(
    r"(?P<repo>checkmk/check-mk-(?:raw|community))@"
    r"(?P<digest>sha256:[0-9a-f]{64})(?P<suffix>\s*(?:#.*)?)"
)
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
LOCK_PATH = Path(".github/supply-chain-lock.json")


class PinError(RuntimeError):
    """Raised when a mutable dependency cannot be resolved safely."""


def request_json(url: str, *, headers: dict[str, str] | None = None) -> Any:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise PinError(f"request failed for {url}: {exc}") from exc


def github_headers() -> dict[str, str]:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def resolve_action(repo: str, ref: str) -> str:
    if FULL_SHA_RE.fullmatch(ref):
        return ref
    encoded_ref = urllib.parse.quote(ref, safe="")
    data = request_json(
        f"https://api.github.com/repos/{repo}/git/ref/tags/{encoded_ref}",
        headers=github_headers(),
    )
    obj = data.get("object") if isinstance(data, dict) else None
    if not isinstance(obj, dict):
        raise PinError(f"GitHub returned no object for {repo}@{ref}")
    if obj.get("type") == "tag":
        tag_url = obj.get("url")
        if not isinstance(tag_url, str):
            raise PinError(f"annotated tag {repo}@{ref} has no object URL")
        tag_data = request_json(tag_url, headers=github_headers())
        obj = tag_data.get("object") if isinstance(tag_data, dict) else None
    sha = obj.get("sha") if isinstance(obj, dict) else None
    if not isinstance(sha, str) or not FULL_SHA_RE.fullmatch(sha):
        raise PinError(f"{repo}@{ref} did not resolve to a commit SHA")
    return sha


def docker_token(repository: str) -> str:
    query = urllib.parse.urlencode(
        {
            "service": "registry.docker.io",
            "scope": f"repository:{repository}:pull",
        }
    )
    data = request_json(f"https://auth.docker.io/token?{query}")
    token = data.get("token") if isinstance(data, dict) else None
    if not isinstance(token, str) or not token:
        raise PinError(f"Docker Hub returned no token for {repository}")
    return token


def resolve_image(repository: str, tag: str) -> str:
    token = docker_token(repository)
    request = urllib.request.Request(
        f"https://registry-1.docker.io/v2/{repository}/manifests/"
        f"{urllib.parse.quote(tag, safe='')}",
        method="HEAD",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": ", ".join(
                (
                    "application/vnd.oci.image.index.v1+json",
                    "application/vnd.docker.distribution.manifest.list.v2+json",
                    "application/vnd.oci.image.manifest.v1+json",
                    "application/vnd.docker.distribution.manifest.v2+json",
                )
            ),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            digest = response.headers.get("Docker-Content-Digest")
    except urllib.error.URLError as exc:
        raise PinError(f"cannot resolve {repository}:{tag}: {exc}") from exc
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        raise PinError(f"registry returned no valid digest for {repository}:{tag}")
    return digest


def source_comment(suffix: str, fallback: str) -> str:
    comment = suffix.strip()
    if comment.startswith("#"):
        value = comment[1:].strip()
        if value:
            return value
    return fallback


def pin_workflow(path: Path, *, write: bool) -> tuple[dict[str, Any], bool]:
    original = path.read_text(encoding="utf-8")
    lines: list[str] = []
    action_locks: dict[str, dict[str, str]] = {}
    image_locks: dict[str, dict[str, str]] = {}

    for line in original.splitlines(keepends=True):
        newline = "\n" if line.endswith("\n") else ""
        body = line[:-1] if newline else line

        action_match = ACTION_RE.search(body)
        if action_match:
            repo = action_match.group("repo")
            ref = action_match.group("ref")
            source_ref = source_comment(action_match.group("suffix"), ref)
            sha = ref if FULL_SHA_RE.fullmatch(ref) else resolve_action(repo, ref)
            action_locks[f"{repo}@{source_ref}"] = {
                "repository": repo,
                "source_ref": source_ref,
                "commit": sha,
            }
            body = (
                body[: action_match.start()]
                + action_match.group("prefix")
                + repo
                + "@"
                + sha
                + f" # {source_ref}"
            )

        pinned_images: list[tuple[str, str, str]] = []
        for pinned in IMAGE_DIGEST_RE.finditer(body):
            repository = pinned.group("repo")
            digest = pinned.group("digest")
            tag = source_comment(pinned.group("suffix"), "digest-pinned")
            pinned_images.append((repository, tag, digest))
        for repository, tag, digest in pinned_images:
            image_locks[f"{repository}:{tag}"] = {
                "repository": repository,
                "source_tag": tag,
                "digest": digest,
            }

        def replace_image(match: re.Match[str]) -> str:
            repository = match.group("repo")
            tag = match.group("tag")
            digest = resolve_image(repository, tag)
            image_locks[f"{repository}:{tag}"] = {
                "repository": repository,
                "source_tag": tag,
                "digest": digest,
            }
            return f"{repository}@{digest} # {tag}"

        if not pinned_images:
            body = IMAGE_TAG_RE.sub(replace_image, body)
        lines.append(body + newline)

    updated = "".join(lines)
    changed = updated != original
    if changed and write:
        path.write_text(updated, encoding="utf-8")
    return {"actions": action_locks, "images": image_locks}, changed


def workflow_files(root: Path) -> list[Path]:
    workflow_dir = root / ".github" / "workflows"
    return sorted(
        path
        for path in workflow_dir.iterdir()
        if path.is_file() and path.suffix in {".yml", ".yaml"}
    )


def canonical_lock(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def generate(root: Path, *, write: bool) -> tuple[dict[str, Any], list[Path]]:
    combined: dict[str, dict[str, Any]] = {"actions": {}, "images": {}}
    changed: list[Path] = []
    for workflow in workflow_files(root):
        locks, workflow_changed = pin_workflow(workflow, write=write)
        combined["actions"].update(locks["actions"])
        combined["images"].update(locks["images"])
        if workflow_changed:
            changed.append(workflow)

    lock = {
        "schema_version": 1,
        "actions": dict(sorted(combined["actions"].items())),
        "images": dict(sorted(combined["images"].items())),
    }
    lock_text = canonical_lock(lock)
    lock_path = root / LOCK_PATH
    previous = lock_path.read_text(encoding="utf-8") if lock_path.exists() else ""
    if previous != lock_text:
        changed.append(lock_path)
        if write:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path.write_text(lock_text, encoding="utf-8")
    return lock, changed


def validate_locked_workflows(root: Path) -> list[str]:
    errors: list[str] = []
    for path in workflow_files(root):
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            match = ACTION_RE.search(line)
            if match and not FULL_SHA_RE.fullmatch(match.group("ref")):
                errors.append(
                    f"{path.relative_to(root)}:{number}: mutable action "
                    f"{match.group('repo')}@{match.group('ref')}"
                )
            for image in IMAGE_TAG_RE.finditer(line):
                errors.append(
                    f"{path.relative_to(root)}:{number}: mutable image {image.group(0)}"
                )
    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    try:
        if args.check:
            errors = validate_locked_workflows(root)
            if errors:
                print("\n".join(errors), file=sys.stderr)
                return 1
            expected, changed = generate(root, write=False)
            if changed:
                for path in changed:
                    print(
                        f"supply-chain lock drift: {path.relative_to(root)}",
                        file=sys.stderr,
                    )
                return 1
            print(
                f"Validated {len(expected['actions'])} action pins and "
                f"{len(expected['images'])} image pins."
            )
            return 0

        lock, changed = generate(root, write=args.write)
    except (OSError, PinError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for path in changed:
        print(f"Updated {path.relative_to(root)}")
    print(
        f"Resolved {len(lock['actions'])} action pins and "
        f"{len(lock['images'])} image pins."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
