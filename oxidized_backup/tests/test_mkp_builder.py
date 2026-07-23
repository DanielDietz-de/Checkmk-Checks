from __future__ import annotations

import ast
import importlib.util
import io
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
BUILDER_PATH = ROOT / "tools/build_mkp.py"
spec = importlib.util.spec_from_file_location("oxidized_backup_mkp_builder", BUILDER_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_builds_deterministic_mkp_with_all_components(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first, first_checksum = module.build_package(
        package_root=ROOT,
        output_dir=first_dir,
        version="1.1.0",
        repository="DanielDietz-de/Checkmk-Checks",
        packaged_version="2.4.0p34",
    )
    second, second_checksum = module.build_package(
        package_root=ROOT,
        output_dir=second_dir,
        version="1.1.0",
        repository="DanielDietz-de/Checkmk-Checks",
        packaged_version="2.4.0p34",
    )

    assert first.read_bytes() == second.read_bytes()
    assert first_checksum.read_text(encoding="utf-8").split()[0] == (
        second_checksum.read_text(encoding="utf-8").split()[0]
    )

    with tarfile.open(first, "r:*") as outer:
        assert {member.name for member in outer.getmembers()} == {
            "info",
            "info.json",
            "agents.tar",
            "cmk_addons_plugins.tar",
            "lib.tar",
        }
        info_file = outer.extractfile("info")
        info_json_file = outer.extractfile("info.json")
        assert info_file is not None and info_json_file is not None
        info = ast.literal_eval(info_file.read().decode("utf-8"))
        assert json.loads(info_json_file.read().decode("utf-8")) == info
        assert info["version"] == "1.1.0"
        assert info["files"]["agents"] == ["plugins/oxidized_backup"]
        assert info["files"]["lib"] == [
            "python3/cmk/base/cee/plugins/bakery/oxidized_backup.py"
        ]
        assert "oxidized_backup/bakery_common.py" in info["files"][
            "cmk_addons_plugins"
        ]
        assert (
            "oxidized_backup/rulesets/ruleset_oxidized_backup_bakery.py"
            in info["files"]["cmk_addons_plugins"]
        )

        for component, required in info["files"].items():
            component_file = outer.extractfile(f"{component}.tar")
            assert component_file is not None
            with tarfile.open(
                fileobj=io.BytesIO(component_file.read()), mode="r:*"
            ) as inner:
                names = {member.name for member in inner.getmembers()}
            assert set(required) <= names


def test_rejects_invalid_version_and_repository(tmp_path: Path) -> None:
    for version, repository in (
        ("latest", "DanielDietz-de/Checkmk-Checks"),
        ("1.1.0", "not-a-repository"),
    ):
        try:
            module.build_package(
                package_root=ROOT,
                output_dir=tmp_path,
                version=version,
                repository=repository,
                packaged_version="2.4.0p34",
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Unsafe package metadata was accepted")
