import ast
import json
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).parents[1]
MODULE_PATH = PACKAGE_ROOT / "src" / "endpoint_age" / "libexec" / "agent_endpoint_age"
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
    target = module.validate_public_https_url("https://status.example/data")
    assert target.url == "https://status.example/data"
    assert target.address == "8.8.8.8"
    assert target.hostname == "status.example"
    with pytest.raises(module.EndpointError, match="HTTPS"):
        module.validate_public_https_url("http://status.example/data")
    monkeypatch.setattr(module.socket, "getaddrinfo", private_dns)
    with pytest.raises(module.EndpointError, match="non-public"):
        module.validate_public_https_url("https://localhost/data")


def test_dns_result_is_pinned_with_original_tls_hostname(monkeypatch):
    dns_calls = []
    pool_calls = {}

    def counted_dns(*args, **kwargs):
        dns_calls.append((args, kwargs))
        return public_dns(*args, **kwargs)

    class RawResponse:
        status = 200
        headers = {}

        def stream(self, amt, decode_content):
            yield b""

        def release_conn(self):
            pool_calls["released"] = True

    class Pool:
        def __init__(self, host, **kwargs):
            pool_calls["host"] = host
            pool_calls["kwargs"] = kwargs

        def urlopen(self, method, target, **kwargs):
            pool_calls["method"] = method
            pool_calls["target"] = target
            pool_calls["request"] = kwargs
            return RawResponse()

        def close(self):
            pool_calls["closed"] = True

    monkeypatch.setattr(module.socket, "getaddrinfo", counted_dns)
    monkeypatch.setattr(module.urllib3, "HTTPSConnectionPool", Pool)

    target = module.validate_public_https_url(
        "https://status.example:8443/data?q=1"
    )
    response = module.pinned_https_get(
        target,
        headers={"User-Agent": "test"},
        timeout=5,
    )
    response.close()

    assert len(dns_calls) == 1
    assert pool_calls["host"] == "8.8.8.8"
    assert pool_calls["kwargs"]["port"] == 8443
    assert pool_calls["kwargs"]["assert_hostname"] == "status.example"
    assert pool_calls["kwargs"]["server_hostname"] == "status.example"
    assert pool_calls["target"] == "/data?q=1"
    assert pool_calls["request"]["headers"]["Host"] == "status.example:8443"
    assert pool_calls["request"]["assert_same_host"] is False


def test_overlong_url_is_rejected_without_truncation(monkeypatch):
    monkeypatch.setattr(module.socket, "getaddrinfo", public_dns)
    url = "https://status.example/" + "x" * module.MAX_URL_LENGTH
    with pytest.raises(module.EndpointError, match="must not exceed"):
        module.validate_public_https_url(url)


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


def test_package_metadata_representations_match():
    python_info = ast.literal_eval(
        (PACKAGE_ROOT / "src" / "info").read_text(encoding="utf-8")
    )
    json_info = json.loads(
        (PACKAGE_ROOT / "src" / "info.json").read_text(encoding="utf-8")
    )
    assert python_info == json_info
