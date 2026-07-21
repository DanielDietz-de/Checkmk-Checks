import json
from pathlib import Path

import pytest

import update_readmes


def write_info(package: Path, data: dict, *, json_only: bool = False):
    (package / "src").mkdir(parents=True)
    if json_only:
        (package / "src" / "info.json").write_text(json.dumps(data), encoding="utf-8")
    else:
        (package / "src" / "info").write_text(repr(data), encoding="utf-8")


def metadata(**overrides):
    data = {
        "name": "example",
        "version": "1.0.0",
        "version.min_required": "2.4.0",
        "version.packaged": "2.4.0p34",
        "files": {"cmk_addons_plugins": ["example/agent_based/check.py"]},
    }
    data.update(overrides)
    return data


def test_info_json_only_packages_are_discovered(tmp_path):
    package = tmp_path / "example"
    write_info(package, metadata(), json_only=True)
    packages = update_readmes.discover_packages(tmp_path)
    assert [item.data["name"] for item in packages] == ["example"]


def test_upper_badge_is_rendered_only_when_explicit():
    without_cap = update_readmes.build_block(metadata())
    with_cap = update_readmes.build_block(
        metadata(**{"version.usable_until": "2.5.99"})
    )
    assert "usable%20until" not in without_cap
    assert "2.5.99" in with_cap


def test_conflicting_info_and_info_json_fail(tmp_path):
    package = tmp_path / "example"
    write_info(package, metadata())
    (package / "src" / "info.json").write_text(
        json.dumps(metadata(**{"version.usable_until": "2.5.99"})),
        encoding="utf-8",
    )
    with pytest.raises(update_readmes.MetadataError, match="metadata mismatch"):
        update_readmes.load_package_metadata(package)


def test_legacy_layout_without_cap_is_reported(tmp_path):
    package = tmp_path / "legacy"
    write_info(
        package,
        metadata(files={"agent_based": ["legacy.py"]}),
    )
    loaded = update_readmes.load_package_metadata(package)
    assert loaded is not None
    warnings = update_readmes.validate_legacy_cap(loaded)
    assert warnings and "version.usable_until" in warnings[0]


def test_legacy_layout_with_cap_is_not_reported(tmp_path):
    package = tmp_path / "legacy"
    write_info(
        package,
        metadata(
            files={"agent_based": ["legacy.py"]},
            **{"version.usable_until": "2.2.99"},
        ),
    )
    loaded = update_readmes.load_package_metadata(package)
    assert loaded is not None
    assert update_readmes.validate_legacy_cap(loaded) == []
