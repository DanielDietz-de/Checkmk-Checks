from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/stage_repository_release.py"


def _load():
    spec = importlib.util.spec_from_file_location("stage_repository_release", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_package(repository: Path, dist: Path, package_dir: str, name: str) -> None:
    (repository / package_dir / "src").mkdir(parents=True)
    (repository / package_dir / "src/info").write_text("{}", encoding="utf-8")
    output_dir = dist / package_dir
    output_dir.mkdir(parents=True)
    manifest = {
        "name": name,
        "version": "1.0.1",
        "version.min_required": "2.4.0",
        "files": {},
    }
    archive_path = output_dir / f"{name}-1.0.1.mkp"
    payload = (repr(manifest) + "\n").encode()
    with tarfile.open(archive_path, mode="w:gz") as archive:
        member = tarfile.TarInfo("info")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    archive_path.with_name(archive_path.name + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n",
        encoding="utf-8",
    )


def _write_index(dist: Path, entries: list[dict[str, str]]) -> None:
    (dist / "packages.json").write_text(json.dumps(entries), encoding="utf-8")


def test_complete_validated_set_is_staged(tmp_path: Path) -> None:
    module = _load()
    repository = tmp_path / "repo"
    dist = tmp_path / "dist"
    _write_package(repository, dist, "alpha", "alpha")
    _write_package(repository, dist, "beta", "beta")
    _write_index(
        dist,
        [
            {"package_dir": "alpha", "name": "alpha", "version": "1.0.1", "path": "alpha/alpha-1.0.1.mkp"},
            {"package_dir": "beta", "name": "beta", "version": "1.0.1", "path": "beta/beta-1.0.1.mkp"},
        ],
    )
    assert module.stage_release(repository, dist) == 2
    assert "'version': '1.0.1'" in (repository / "alpha/src/info").read_text(encoding="utf-8")
    assert (repository / "beta/beta-1.0.1.mkp").is_file()


def test_partial_artifact_set_is_rejected(tmp_path: Path) -> None:
    module = _load()
    repository = tmp_path / "repo"
    dist = tmp_path / "dist"
    _write_package(repository, dist, "alpha", "alpha")
    (repository / "beta/src").mkdir(parents=True)
    (repository / "beta/src/info").write_text("{}", encoding="utf-8")
    _write_index(
        dist,
        [{"package_dir": "alpha", "name": "alpha", "version": "1.0.1", "path": "alpha/alpha-1.0.1.mkp"}],
    )
    with pytest.raises(ValueError, match="not complete"):
        module.stage_release(repository, dist)


def test_path_traversal_is_rejected(tmp_path: Path) -> None:
    module = _load()
    repository = tmp_path / "repo"
    dist = tmp_path / "dist"
    (repository / "alpha/src").mkdir(parents=True)
    (repository / "alpha/src/info").write_text("{}", encoding="utf-8")
    dist.mkdir()
    _write_index(
        dist,
        [{"package_dir": "alpha", "name": "alpha", "version": "1.0.1", "path": "../escape.mkp"}],
    )
    with pytest.raises(ValueError, match="unsafe relative path"):
        module.stage_release(repository, dist)


def test_manifest_metadata_mismatch_is_rejected(tmp_path: Path) -> None:
    module = _load()
    repository = tmp_path / "repo"
    dist = tmp_path / "dist"
    _write_package(repository, dist, "alpha", "alpha")
    _write_index(
        dist,
        [{"package_dir": "alpha", "name": "other", "version": "1.0.1", "path": "alpha/alpha-1.0.1.mkp"}],
    )
    with pytest.raises(ValueError, match="package name"):
        module.stage_release(repository, dist)
