#!/usr/bin/env python3
"""Build every active top-level Checkmk package from its canonical src/info.

The repository source layout mirrors the paths stored in each MKP component.
This builder creates deterministic MKP archives without depending on a
pre-existing Checkmk site, then validates their manifests and checksums.
"""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import io
import json
import os
import pprint
import stat
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

PACKAGED_VERSION = "2.5.0p9"
USABLE_UNTIL = "2.5.99"

# Source roots below <package>/src for each Checkmk package component. Some
# packages retain the older cmk/plugins source layout while their MKP component
# is still named cmk_plugins. Keep both layouts readable during normalization.
_COMPONENT_SOURCE_ROOTS = {
    "agent_based": (Path("base/plugins/agent_based"),),
    "agents": (Path("agents"),),
    "alert_handlers": (Path("alert_handlers"),),
    "bin": (Path("bin"),),
    "checkman": (Path("checkman"),),
    "checks": (Path("checks"),),
    "cmk_addons_plugins": (Path("."),),
    "cmk_plugins": (Path("cmk_plugins"), Path("cmk/plugins")),
    "doc": (Path("doc"),),
    "inventory": (Path("inventory"),),
    "lib": (Path("lib"),),
    "locales": (Path("locales"),),
    "mibs": (Path("mibs"),),
    "notifications": (Path("notifications"),),
    "pnp-rraconf": (Path("pnp-rraconf"),),
    "pnp-templates": (Path("pnp-templates"),),
    "web": (Path("web"),),
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("dist/repository-mkps"))
    parser.add_argument("--package", action="append", default=[])
    parser.add_argument("--packaged-version", default=PACKAGED_VERSION)
    parser.add_argument("--usable-until", default=USABLE_UNTIL)
    return parser.parse_args()


def discover_package_dirs(repository: Path, selected: list[str]) -> list[Path]:
    if selected:
        package_dirs = [repository / value for value in selected]
    else:
        package_dirs = [path.parent.parent for path in repository.glob("*/src/info")]
    package_dirs = sorted({path.resolve() for path in package_dirs})
    errors = [str(path) for path in package_dirs if not (path / "src" / "info").is_file()]
    if errors:
        raise SystemExit(f"Missing canonical src/info for: {errors}")
    return package_dirs


def read_manifest(package_dir: Path, packaged_version: str, usable_until: str) -> dict[str, Any]:
    info_path = package_dir / "src" / "info"
    manifest = ast.literal_eval(info_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"{info_path}: manifest is not a dictionary")

    required = {
        "name",
        "title",
        "author",
        "description",
        "version",
        "version.min_required",
        "files",
    }
    missing = sorted(required - manifest.keys())
    if missing:
        raise ValueError(f"{info_path}: missing fields {missing}")
    if not isinstance(manifest["files"], dict):
        raise ValueError(f"{info_path}: files must be a dictionary")

    manifest = dict(manifest)
    manifest["version"] = str(manifest["version"])
    manifest["version.min_required"] = str(manifest["version.min_required"])
    manifest["version.packaged"] = packaged_version
    manifest["version.usable_until"] = usable_until
    manifest["download_url"] = (
        "https://github.com/DanielDietz-de/Checkmk-Checks/tree/master/"
        f"{package_dir.name}"
    )

    normalized_files: dict[str, list[str]] = {}
    for component, entries in manifest["files"].items():
        if component not in _COMPONENT_SOURCE_ROOTS:
            raise ValueError(f"{info_path}: unsupported package component {component!r}")
        if not isinstance(entries, list) or not all(isinstance(entry, str) for entry in entries):
            raise ValueError(f"{info_path}: component {component!r} must contain a list of paths")
        normalized_files[component] = sorted(dict.fromkeys(entries))
    manifest["files"] = dict(sorted(normalized_files.items()))
    return manifest


def _safe_relative_path(value: str) -> PurePosixPath:
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or value in {"", "."}:
        raise ValueError(f"Unsafe package path: {value!r}")
    return relative


def _source_path(package_dir: Path, component: str, relative: str) -> Path:
    safe_relative = _safe_relative_path(relative)
    candidates: list[Path] = []
    for source_root in _COMPONENT_SOURCE_ROOTS[component]:
        root = package_dir / "src" / source_root
        source = root.joinpath(*safe_relative.parts)
        candidates.append(source)
        if not source.exists() and not source.is_symlink():
            continue

        resolved_root = root.resolve()
        if source.is_symlink():
            # Symlinks are archived as symlinks; only their location must remain
            # inside the selected package source root.
            parent = source.parent.resolve()
            if not parent.is_relative_to(resolved_root):
                raise ValueError(f"{source}: symlink parent escapes package source root")
        elif not source.resolve().is_relative_to(resolved_root):
            raise ValueError(f"{source}: source path escapes package source root")
        return source

    raise FileNotFoundError(
        f"{package_dir.name}: missing source for {component}:{relative}; "
        f"checked {[str(path) for path in candidates]}"
    )


def _tarinfo_for(source: Path, arcname: str) -> tuple[tarfile.TarInfo, io.BufferedReader | None]:
    info = tarfile.TarInfo(arcname)
    st = source.lstat()
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mode = stat.S_IMODE(st.st_mode)

    if source.is_symlink():
        info.type = tarfile.SYMTYPE
        info.linkname = os.readlink(source)
        info.size = 0
        return info, None
    if not source.is_file():
        raise ValueError(f"Unsupported package source type: {source}")
    info.type = tarfile.REGTYPE
    info.size = st.st_size
    return info, source.open("rb")


def _component_tar(package_dir: Path, component: str, files: list[str]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for relative in files:
            source = _source_path(package_dir, component, relative)
            info, fileobj = _tarinfo_for(source, relative)
            try:
                archive.addfile(info, fileobj)
            finally:
                if fileobj is not None:
                    fileobj.close()
    return buffer.getvalue()


def _add_bytes(archive: tarfile.TarFile, name: str, content: bytes, mode: int = 0o644) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(content)
    info.mode = mode
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    archive.addfile(info, io.BytesIO(content))


def build_package(package_dir: Path, output_root: Path, manifest: dict[str, Any]) -> Path:
    package_output = output_root / package_dir.name
    package_output.mkdir(parents=True, exist_ok=True)
    filename = f"{manifest['name']}-{manifest['version']}.mkp"
    package_path = package_output / filename

    python_info = (pprint.pformat(manifest, sort_dicts=False, width=120) + "\n").encode()
    json_info = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()

    with package_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as outer:
                _add_bytes(outer, "info", python_info)
                _add_bytes(outer, "info.json", json_info)
                for component, files in manifest["files"].items():
                    _add_bytes(outer, f"{component}.tar", _component_tar(package_dir, component, files))

    checksum = hashlib.sha256(package_path.read_bytes()).hexdigest()
    checksum_path = package_path.with_name(package_path.name + ".sha256")
    checksum_path.write_text(f"{checksum}  {package_path.name}\n", encoding="utf-8")
    verify_package(package_path, manifest)
    return package_path


def verify_package(package_path: Path, expected: dict[str, Any]) -> None:
    with tarfile.open(package_path, mode="r:gz") as outer:
        members = {PurePosixPath(member.name).name: member for member in outer.getmembers()}
        required = {"info", "info.json"} | {f"{part}.tar" for part in expected["files"]}
        missing = sorted(required - members.keys())
        if missing:
            raise ValueError(f"{package_path}: missing outer members {missing}")

        info_file = outer.extractfile(members["info"])
        json_file = outer.extractfile(members["info.json"])
        if info_file is None or json_file is None:
            raise ValueError(f"{package_path}: unreadable package metadata")
        parsed_info = ast.literal_eval(info_file.read().decode("utf-8"))
        parsed_json = json.loads(json_file.read().decode("utf-8"))
        if parsed_info != expected or parsed_json != expected:
            raise ValueError(f"{package_path}: manifest serialization mismatch")

        for component, expected_files in expected["files"].items():
            component_file = outer.extractfile(members[f"{component}.tar"])
            if component_file is None:
                raise ValueError(f"{package_path}: unreadable {component}.tar")
            with tarfile.open(fileobj=component_file, mode="r:") as inner:
                actual = sorted(
                    member.name.removeprefix("./")
                    for member in inner.getmembers()
                    if member.isfile() or member.issym()
                )
            if actual != sorted(expected_files):
                raise ValueError(
                    f"{package_path}: {component} inventory mismatch; "
                    f"expected={sorted(expected_files)}, actual={actual}"
                )


def main() -> None:
    args = _parse_args()
    repository = args.repository.resolve()
    output_root = args.output.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    metadata: list[dict[str, str]] = []
    for package_dir in discover_package_dirs(repository, args.package):
        manifest = read_manifest(package_dir, args.packaged_version, args.usable_until)
        package_path = build_package(package_dir, output_root, manifest)
        relative_output = package_path.relative_to(output_root)
        metadata.append(
            {
                "package_dir": package_dir.name,
                "name": manifest["name"],
                "version": manifest["version"],
                "min_required": manifest["version.min_required"],
                "filename": package_path.name,
                "path": relative_output.as_posix(),
            }
        )
        print(f"Built {relative_output}")

    metadata_path = output_root / "packages.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Built {len(metadata)} packages")


if __name__ == "__main__":
    main()
