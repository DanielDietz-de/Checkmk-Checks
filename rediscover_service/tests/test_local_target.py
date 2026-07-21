from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "src" / "notifications" / "rediscover_service"
loader = SourceFileLoader("rediscover_service", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
loader.exec_module(module)


def test_accepts_current_site_on_loopback(monkeypatch):
    monkeypatch.setenv("OMD_SITE", "cmk")
    assert module.local_api_url("http", "127.0.0.1:5000", "cmk") == (
        "http://127.0.0.1:5000/cmk/check_mk/api/1.0"
    )


def test_rejects_remote_host_before_reading_secret(monkeypatch):
    monkeypatch.setenv("OMD_SITE", "cmk")
    with pytest.raises(module.UnsafeSiteTarget, match="loopback"):
        module.local_api_url("https", "monitoring.example", "cmk")


def test_rejects_other_site(monkeypatch):
    monkeypatch.setenv("OMD_SITE", "cmk")
    with pytest.raises(module.UnsafeSiteTarget, match="local site"):
        module.local_api_url("http", "localhost", "other")
