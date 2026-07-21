from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[1]
    / "src"
    / "service_metric_counter"
    / "libexec"
    / "agent_service_metric_counter"
)
loader = SourceFileLoader("agent_service_metric_counter", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
loader.exec_module(module)


def test_accepts_current_site_on_loopback(monkeypatch):
    monkeypatch.setenv("OMD_SITE", "cmk")
    assert module.local_site_base_url("https://localhost/cmk/") == "https://localhost/cmk"


def test_rejects_remote_host_before_reading_secret(monkeypatch):
    monkeypatch.setenv("OMD_SITE", "cmk")
    with pytest.raises(module.UnsafeSiteUrl, match="loopback"):
        module.local_site_base_url("https://monitoring.example/cmk")


def test_rejects_other_local_site(monkeypatch):
    monkeypatch.setenv("OMD_SITE", "cmk")
    with pytest.raises(module.UnsafeSiteUrl, match="local site"):
        module.local_site_base_url("http://localhost/other")
