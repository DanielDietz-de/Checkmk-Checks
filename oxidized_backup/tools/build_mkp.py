#!/usr/bin/env python3
"""Build a deterministic Checkmk MKP for oxidized_backup.

Checkmk's ``mkp package`` command refuses to collect local extension files from
parts of the Checkmk Python namespace because those paths overlap the product
namespace.  Agent Bakery plug-ins must nevertheless be installed in that local
namespace.  This builder creates the documented MKP archive structure directly
and leaves semantic validation to ``mkp inspect`` and a clean ``mkp add`` /
``mkp enable`` installation in CI.
"""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import io
import json
import os
import re
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO

PACKAGE_NAME = "oxidized_backup"
PACKAGE_TITLE = "Oxidized Backup Verification"
PACKAGE_AUTHOR = "Daniel Dietz"
PACKAGE_DESCRIPTION = (
    "Verifies Oxidized collection, Git backup artifacts, repository integrity, "
    "remote Git synchronization, and supports Checkmk Agent Bakery deployment."
)
VERSION_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+){2}(?:[A-Za-z0-9._-]*)?$")


@dataclass(frozen=True)
class Component:
    name: str
    source_root: Path
    include_root: Path


def _safe_relative(path: Path, root: Path) -> PurePosixPath:
    relative = PurePosixPath(path.relative_to(root).as_posix())
    if relative.is_absolute() or not relative.parts:
        raise ValueError(f"Unsafe package path: {relative}")
    if any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError(f"Unsafe package path: {relative}")
    return relative


def _files(component: Component) -> list[tuple[Path, PurePosixPath]]:
    if not component.source_root.is_dir():
        raise FileNotFoundError(component.source_root)
    if not component.include_root.exists():
        raise FileNotFoundError(component.include_root)

    selected: list[tuple[Path, PurePosixPath]] = []
    candidates = (
        [component.include_root]
        if component.include_root.is_file()
        else sorted(component.include_root.rglob("*"))
    )
    for path in candidates:
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        selected.append((path, _safe_relative(path, component.source_root)))
    if not selected:
        raise ValueError(f"Component {component.name!r} contains no files")
    return selected


def _normalise_tar_info(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mtime = 0
    return info


def _gzip_tar_bytes(files: list[tuple[Path, PurePosixPath]]) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for source, relative in files:
                archive.add(
                    source,
                    arcname=str(relative),
                    recursive=False,
                    filter=_normalise_tar_info,
                )
    return output.getvalue()


def _add_bytes(
    archive: tarfile.TarFile,
    name: str,
    content: bytes,
    *,
    mode: int = 0o644,
) -> None:
    relative = PurePosixPath(name)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError(f"Unsafe outer archive path: {name}")
    info = tarfile.TarInfo(name=str(relative))
    info.size = len(content)
    info.mode = mode
    _normalise_tar_info(info)
    archive.addfile(info, io.BytesIO(content))


def _outer_archive(
    target: Path,
    manifest: dict[str, object],
    component_archives: dict[str, bytes],
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as gz:
                with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as archive:
                    _add_bytes(
                        archive,
                        "info",
                        (repr(manifest) + "\n").encode("utf-8"),
                    )
                    _add_bytes(
                        archive,
                        "info.json",
                        (
                            json.dumps(
                                manifest,
                                indent=2,
                                sort_keys=True,
                                ensure_ascii=False,
                            )
                            + "\n"
                        ).encode("utf-8"),
                    )
                    for component_name in sorted(component_archives):
                        _add_bytes(
                            archive,
                            f"{component_name}.tar",
                            component_archives[component_name],
                        )
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _validate_package(target: Path, manifest: dict[str, object]) -> None:
    with tarfile.open(target, "r:*") as outer:
        outer_names = {member.name for member in outer.getmembers()}
        expected_outer = {"info", "info.json"} | {
            f"{component}.tar" for component in manifest["files"]  # type: ignore[index]
        }
        if outer_names != expected_outer:
            raise ValueError(
                f"Unexpected outer archive members: {sorted(outer_names ^ expected_outer)}"
            )
        info = outer.extractfile("info")
        info_json = outer.extractfile("info.json")
        if info is None or info_json is None:
            raise ValueError("MKP metadata is unreadable")
        if ast.literal_eval(info.read().decode("utf-8")) != manifest:
            raise ValueError("info metadata does not match the manifest")
        if json.loads(info_json.read().decode("utf-8")) != manifest:
            raise ValueError("info.json metadata does not match the manifest")

        files_by_component = manifest["files"]  # type: ignore[index]
        if not isinstance(files_by_component, dict):
            raise ValueError("Manifest files field is invalid")
        for component, required in files_by_component.items():
            member = outer.extractfile(f"{component}.tar")
            if member is None:
                raise ValueError(f"Unable to read {component}.tar")
            with tarfile.open(fileobj=io.BytesIO(member.read()), mode="r:*") as inner:
                names = {item.name.removeprefix("./") for item in inner.getmembers()}
            missing = set(required) - names
            if missing:
                raise ValueError(
                    f"Component {component!r} is missing files: {sorted(missing)}"
                )


def build_package(
    *,
    package_root: Path,
    output_dir: Path,
    version: str,
    repository: str,
    packaged_version: str,
) -> tuple[Path, Path]:
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError(f"Invalid package version: {version}")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError(f"Invalid repository name: {repository}")

    components = (
        Component(
            name="agents",
            source_root=package_root / "src" / "agents",
            include_root=package_root / "src" / "agents" / "plugins" / PACKAGE_NAME,
        ),
        Component(
            name="cmk_addons_plugins",
            source_root=package_root / "src",
            include_root=package_root / "src" / PACKAGE_NAME,
        ),
        Component(
            name="lib",
            source_root=package_root / "src" / "lib",
            include_root=(
                package_root
                / "src"
                / "lib"
                / "python3"
                / "cmk"
                / "base"
                / "cee"
                / "plugins"
                / "bakery"
                / f"{PACKAGE_NAME}.py"
            ),
        ),
    )

    selected = {component.name: _files(component) for component in components}
    files_manifest = {
        component_name: [str(relative) for _source, relative in files]
        for component_name, files in selected.items()
    }
    manifest: dict[str, object] = {
        "name": PACKAGE_NAME,
        "title": PACKAGE_TITLE,
        "author": PACKAGE_AUTHOR,
        "description": PACKAGE_DESCRIPTION,
        "version": version,
        "version.min_required": "2.4.0b1",
        "version.packaged": packaged_version,
        "version.usable_until": "2.4.99",
        "download_url": (
            f"https://github.com/{repository}/tree/master/{PACKAGE_NAME}"
        ),
        "files": files_manifest,
    }

    component_archives = {
        component_name: _gzip_tar_bytes(files)
        for component_name, files in selected.items()
    }
    target = output_dir / f"{PACKAGE_NAME}-{version}.mkp"
    _outer_archive(target, manifest, component_archives)
    _validate_package(target, manifest)

    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    checksum = target.with_name(f"{target.name}.sha256")
    checksum.write_text(f"{digest}  {target.name}\n", encoding="utf-8")
    return target, checksum


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--repository",
        default=os.environ.get("GITHUB_REPOSITORY", "DanielDietz-de/Checkmk-Checks"),
    )
    parser.add_argument("--packaged-version", default="2.4.0p34")
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package_root = Path(__file__).resolve().parents[1]
    output_dir = args.output_dir or package_root
    package, checksum = build_package(
        package_root=package_root,
        output_dir=output_dir,
        version=args.version,
        repository=args.repository,
        packaged_version=args.packaged_version,
    )
    print(package)
    print(checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
