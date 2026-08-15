from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/detect_affected_packages.py"


def _load():
    """Handle load for this module's workflow."""
    spec = importlib.util.spec_from_file_location("detect_affected_packages", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _repository(tmp_path: Path) -> Path:
    """Handle repository for this module's workflow."""
    for name in ("alpha", "beta"):
        (tmp_path / name / "src").mkdir(parents=True)
        (tmp_path / name / "src/info").write_text("{}", encoding="utf-8")
    return tmp_path


def test_package_local_changes_are_targeted(tmp_path: Path) -> None:
    """Verify that package local changes are targeted."""
    module = _load()
    result = module.classify_changes(
        _repository(tmp_path),
        [
            module.Change("M", ("alpha/src/plugin.py",)),
            module.Change("A", ("beta/tests/test_beta.py",)),
        ],
    )
    assert result.mode == "targeted"
    assert result.packages == ("alpha", "beta")


@pytest.mark.parametrize(
    "path",
    [
        ".github/scripts/build_repository_mkps.py",
        ".github/workflows/repository-mkp-ci.yml",
        "tools/ci/full_repository_audit.py",
        ".github/repository-mkp-release.json",
        "mkp_index.json",
    ],
)
def test_shared_inputs_force_full_validation(tmp_path: Path, path: str) -> None:
    """Verify that shared inputs force full validation."""
    module = _load()
    result = module.classify_changes(
        _repository(tmp_path),
        [module.Change("M", (path,))],
    )
    assert result.mode == "full"


@pytest.mark.parametrize("path", ["alpha/src/info", "alpha/src/info.json"])
def test_package_manifest_changes_force_full_validation(tmp_path: Path, path: str) -> None:
    """Verify that package manifest changes force full validation."""
    module = _load()
    result = module.classify_changes(
        _repository(tmp_path),
        [module.Change("M", (path,))],
    )
    assert result.mode == "full"
    assert "package metadata" in result.reason


def test_new_active_package_manifest_forces_full_validation(tmp_path: Path) -> None:
    """Verify that new active package manifest forces full validation."""
    module = _load()
    repository = _repository(tmp_path)
    (repository / "gamma/src").mkdir(parents=True)
    (repository / "gamma/src/info").write_text("{}", encoding="utf-8")
    result = module.classify_changes(
        repository,
        [module.Change("A", ("gamma/src/info",))],
    )
    assert result.mode == "full"


def test_documentation_only_change_skips_expensive_matrix(tmp_path: Path) -> None:
    """Verify that documentation only change skips expensive matrix."""
    module = _load()
    result = module.classify_changes(
        _repository(tmp_path),
        [
            module.Change("M", ("alpha/README.md",)),
            module.Change("M", ("docs/CI_ARCHITECTURE.md",)),
        ],
    )
    assert result.mode == "none"
    assert result.packages == ()


@pytest.mark.parametrize("status", ["D", "R100", "C100", "U"])
def test_rename_delete_copy_and_unknown_status_fail_safe(tmp_path: Path, status: str) -> None:
    """Verify that rename delete copy and unknown status fail safe."""
    module = _load()
    paths = (
        ("alpha/src/old.py", "alpha/src/new.py")
        if status[:1] in {"R", "C"}
        else ("alpha/src/plugin.py",)
    )
    result = module.classify_changes(
        _repository(tmp_path),
        [module.Change(status, paths)],
    )
    assert result.mode == "full"


def test_unmapped_or_ambiguous_paths_fail_safe(tmp_path: Path) -> None:
    """Verify that unmapped or ambiguous paths fail safe."""
    module = _load()
    repository = _repository(tmp_path)
    assert module.classify_changes(
        repository,
        [module.Change("M", ("unknown/file.txt",))],
    ).mode == "full"
    assert module.classify_changes(
        repository,
        [module.Change("M", ("alpha/config.yaml",))],
    ).mode == "full"


def test_newline_path_fails_safe_without_output_injection(tmp_path: Path) -> None:
    """Verify that newline path fails safe without output injection."""
    module = _load()
    result = module.classify_changes(
        _repository(tmp_path),
        [module.Change("M", (".github/scripts/x\nmode=none",))],
    )
    assert result.mode == "full"
    output = tmp_path / "github-output"
    module._write_github_output(output, result)
    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "mode=full"
    assert sum(line.startswith("mode=") for line in lines) == 1
    assert "\\nmode=none" in lines[-1]


def test_all_output_values_are_single_line(tmp_path: Path) -> None:
    """Verify that all output values are single line."""
    module = _load()
    output = tmp_path / "github-output"
    module._write_github_output(
        output,
        module.Selection("full", ("alpha\npackage",), "reason\r\nmode=none"),
    )
    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4
    assert lines[0] == "mode=full"
    assert lines[1] == 'packages=["alpha\\npackage"]'
    assert lines[3] == "reason=reason\\r\\nmode=none"


def test_non_pull_request_events_are_always_full(tmp_path: Path) -> None:
    """Verify that non pull request events are always full."""
    module = _load()
    result = module.select_for_event(
        _repository(tmp_path),
        event_name="push",
        ref="refs/heads/master",
        base="ignored",
        head="ignored",
    )
    assert result.mode == "full"


def test_name_status_parser_handles_renames() -> None:
    """Verify that name status parser handles renames."""
    module = _load()
    changes = module.parse_name_status(
        b"M\0alpha/src/a.py\0R100\0alpha/src/old.py\0alpha/src/new.py\0"
    )
    assert changes == [
        module.Change("M", ("alpha/src/a.py",)),
        module.Change("R100", ("alpha/src/old.py", "alpha/src/new.py")),
    ]


def test_truncated_name_status_is_rejected() -> None:
    """Verify that truncated name status is rejected."""
    module = _load()
    with pytest.raises(ValueError, match="truncated"):
        module.parse_name_status(b"R100\0alpha/src/old.py\0")
