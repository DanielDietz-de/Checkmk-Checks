from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/verify_repository_release.py"


def _load():
    spec = importlib.util.spec_from_file_location("verify_repository_release", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _dist(path: Path, payload: bytes = b"package") -> Path:
    (path / "alpha").mkdir(parents=True)
    package = path / "alpha/alpha-1.0.0.mkp"
    package.write_bytes(payload)
    (path / "packages.json").write_text(
        json.dumps(
            [
                {
                    "package_dir": "alpha",
                    "name": "alpha",
                    "version": "1.0.0",
                    "path": "alpha/alpha-1.0.0.mkp",
                }
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_identical_artifacts_are_accepted(tmp_path: Path) -> None:
    module = _load()
    assert module.verify_artifacts(_dist(tmp_path / "a"), _dist(tmp_path / "b")) == 1


def test_nondeterministic_artifacts_are_rejected(tmp_path: Path) -> None:
    module = _load()
    with pytest.raises(ValueError, match="nondeterministic"):
        module.verify_artifacts(
            _dist(tmp_path / "a", b"first"),
            _dist(tmp_path / "b", b"second"),
        )


def test_unsafe_index_path_is_rejected(tmp_path: Path) -> None:
    module = _load()
    source = _dist(tmp_path / "a")
    rebuilt = _dist(tmp_path / "b")
    for dist in (source, rebuilt):
        index = json.loads((dist / "packages.json").read_text(encoding="utf-8"))
        index[0]["path"] = "../alpha-1.0.0.mkp"
        (dist / "packages.json").write_text(json.dumps(index), encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected package path"):
        module.verify_artifacts(source, rebuilt)


@pytest.mark.parametrize(
    ("path", "allowed"),
    [
        (".github/repository-mkp-release.json", True),
        ("alpha/src/info", True),
        ("alpha/src/info.json", True),
        ("alpha/README.md", True),
        ("alpha/alpha-1.0.0.mkp", True),
        ("alpha/alpha-1.0.0.mkp.sha256", True),
        ("alpha/src/plugin.py", False),
        ("unknown/unknown-1.0.0.mkp", False),
        ("../alpha/alpha-1.0.0.mkp", False),
        (".github/workflows/repository-mkp-ci.yml", False),
    ],
)
def test_generated_path_allowlist(path: str, allowed: bool) -> None:
    module = _load()
    assert module._allowed_generated_path(path, {"alpha"}) is allowed


def test_nul_path_decoder_preserves_newlines() -> None:
    module = _load()
    assert module._decode_nul_paths(b"alpha/README.md\0alpha/line\nbreak.mkp\0") == {
        "alpha/README.md",
        "alpha/line\nbreak.mkp",
    }


def test_release_config_must_be_finalized(tmp_path: Path) -> None:
    module = _load()
    path = tmp_path / ".github"
    path.mkdir()
    (path / "repository-mkp-release.json").write_text(
        json.dumps({"bump_versions": True, "completed": False}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="not finalized"):
        module.verify_release_config(tmp_path)
