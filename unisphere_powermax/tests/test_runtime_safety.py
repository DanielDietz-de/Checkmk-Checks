import json
import os
import stat
import sys
import time
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "src" / "unisphere_powermax" / "libexec" / "agent_unisphere_powermax"
loader = SourceFileLoader("agent_unisphere_powermax_safe", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)


def test_synthetic_failure_flag_no_longer_exists():
    with pytest.raises(SystemExit):
        module.parse_args(
            [
                "--user", "u",
                "--password", "p",
                "--hostname", "host",
                "--randomFailures",
            ]
        )


def test_cache_write_is_atomic_private_json(tmp_path):
    cache = tmp_path / "cache.json"
    data = {"volumes": ["volume"], "ports": ["port"]}
    module.atomic_write_cache(cache, data)
    assert json.loads(cache.read_text(encoding="utf-8")) == data
    assert stat.S_IMODE(cache.stat().st_mode) == 0o600


def test_cache_rejects_symlink(tmp_path):
    target = tmp_path / "target"
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "cache"
    link.symlink_to(target)
    with pytest.raises(module.UnisphereError, match="regular file"):
        module.read_cache(link, 30)


def test_expired_cache_is_not_returned(tmp_path):
    cache = tmp_path / "cache.json"
    module.atomic_write_cache(cache, {"volumes": [], "ports": []})
    os.utime(cache, (time.time() - 3600, time.time() - 3600))
    assert module.read_cache(cache, 1) is None


def test_selected_source_error_fails_main_without_partial_stdout(monkeypatch, capsys):
    class Connector:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, endpoint):
            return {"version": "10"}

        def ensure_symmetrix_info(self):
            pass

    monkeypatch.setattr(module, "PmaxConnector", Connector)
    monkeypatch.setattr(
        module,
        "DATA_SOURCES",
        (("get_srp_info", lambda connector, args: (_ for _ in ()).throw(module.UnisphereError("boom"))),),
    )
    status = module.main(["--user", "u", "--password", "p", "--hostname", "host"])
    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert "boom" in captured.err


def test_clean_item_removes_agent_separator_characters():
    assert module.clean_item("bad|value\nnext") == "bad/value next"
