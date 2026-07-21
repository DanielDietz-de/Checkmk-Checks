import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "src" / "endpoint_age" / "libexec" / "agent_endpoint_age"
loader = SourceFileLoader("agent_endpoint_age_secure", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)


def public_dns(*args, **kwargs):
    return [(module.socket.AF_INET, module.socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]


def private_dns(*args, **kwargs):
    return [(module.socket.AF_INET, module.socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]


def test_requires_public_https(monkeypatch):
    monkeypatch.setattr(module.socket, "getaddrinfo", public_dns)
    assert module.validate_public_https_url("https://status.example/data") == "https://status.example/data"
    with pytest.raises(module.EndpointError, match="HTTPS"):
        module.validate_public_https_url("http://status.example/data")
    monkeypatch.setattr(module.socket, "getaddrinfo", private_dns)
    with pytest.raises(module.EndpointError, match="non-public"):
        module.validate_public_https_url("https://localhost/data")


def test_json_path_is_bounded_and_safe():
    data = {"items": [{"updated": "2026-01-01T00:00:00Z"}]}
    assert module.lookup_json_path(data, "items[0].updated") == "2026-01-01T00:00:00Z"
    assert module.lookup_json_path(data, "x" * 600) is None


def test_custom_headers_are_not_part_of_runtime_spec():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "extra_headers" not in source
    assert "add_header" not in source


def test_response_size_is_bounded():
    class Response:
        def iter_content(self, chunk_size=65536):
            yield b"x" * (module.MAX_RESPONSE_BYTES + 1)
    with pytest.raises(module.EndpointError, match="1 MiB"):
        module.read_bounded(Response())
