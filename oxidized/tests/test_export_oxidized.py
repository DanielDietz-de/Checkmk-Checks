import json
import os
import stat
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "src" / "bin" / "export_oxidized"
loader = SourceFileLoader("export_oxidized", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)


def test_local_secret_target_is_restricted_to_current_loopback_site():
    assert module.validate_local_site_url("http://127.0.0.1:5000/cmk", "cmk") == (
        "http://127.0.0.1:5000/cmk"
    )
    with pytest.raises(module.ExportError, match="loopback"):
        module.validate_local_site_url("https://monitoring.example/cmk", "cmk")
    with pytest.raises(module.ExportError, match="path must be /cmk"):
        module.validate_local_site_url("http://localhost/other", "cmk")


def test_view_parser_sorts_deduplicates_and_validates_os_tags():
    data = [
        ["Host", "Model"],
        ["switch-b", "Device [junos]"],
        ["switch-a", "Device [ios]"],
        ["switch-a", "Device [ios]"],
    ]
    assert module.parse_oxidized_view(data) == [
        {"hostname": "switch-a", "os": "ios"},
        {"hostname": "switch-b", "os": "junos"},
    ]
    with pytest.raises(module.ExportError, match="no valid"):
        module.parse_oxidized_view([["Host", "Model"], ["switch", "missing"]])


def test_conflicting_duplicate_host_fails_closed():
    with pytest.raises(module.ExportError, match="conflicting"):
        module.parse_oxidized_view(
            [["Host", "Model"], ["switch", "[ios]"], ["switch", "[junos]"]]
        )


def test_atomic_output_is_private_and_valid_json(tmp_path):
    output = tmp_path / "oxidized.json"
    inventory = [{"hostname": "switch", "os": "ios"}]
    module.atomic_write_json(output, inventory)
    assert json.loads(output.read_text(encoding="utf-8")) == inventory
    assert stat.S_IMODE(output.stat().st_mode) == 0o640


def test_failed_export_can_remove_active_stale_file(tmp_path):
    output = tmp_path / "oxidized.json"
    output.write_text("old", encoding="utf-8")
    stale = module.invalidate_output(output)
    assert stale is not None and stale.exists()
    assert not output.exists()


def test_secret_file_must_not_be_group_readable(tmp_path):
    secret = tmp_path / "automation.secret"
    secret.write_text("secret", encoding="utf-8")
    os.chmod(secret, 0o640)
    with pytest.raises(module.ExportError, match="group or others"):
        module.validate_secret_file(secret)
    os.chmod(secret, 0o600)
    assert module.validate_secret_file(secret) == secret


def test_output_must_stay_below_omd_root(tmp_path):
    root = tmp_path / "site"
    root.mkdir()
    with pytest.raises(module.ExportError, match="below OMD_ROOT"):
        module.ensure_managed_path(tmp_path / "outside.json", root, "output")
