import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "src" / "status_feed" / "libexec" / "agent_status_feed"
loader = SourceFileLoader("agent_status_feed_secure", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)


def public_dns(*args, **kwargs):
    return [(module.socket.AF_INET, module.socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]


def private_dns(*args, **kwargs):
    return [(module.socket.AF_INET, module.socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443))]


def test_requires_public_https(monkeypatch):
    monkeypatch.setattr(module.socket, "getaddrinfo", public_dns)
    target = module.validate_public_https_url("https://status.example/feed.xml")
    assert target.url == "https://status.example/feed.xml"
    assert target.address == "8.8.8.8"
    monkeypatch.setattr(module.socket, "getaddrinfo", private_dns)
    with pytest.raises(module.FeedError, match="non-public"):
        module.validate_public_https_url("https://internal.example/feed.xml")


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
        "https://status.example:8443/feed.xml?format=rss"
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
    assert pool_calls["target"] == "/feed.xml?format=rss"
    assert pool_calls["request"]["headers"]["Host"] == "status.example:8443"
    assert pool_calls["request"]["assert_same_host"] is False


def test_rejects_dtd_and_entity_documents():
    with pytest.raises(module.FeedError, match="DTD"):
        module.extract_items(b"<!DOCTYPE rss [<!ENTITY x 'boom'>]><rss></rss>")


def test_rejects_declaration_after_large_prefix():
    document = b" " * 5000 + b"<!DOCTYPE rss [<!ENTITY x 'boom'>]><rss></rss>"
    with pytest.raises(module.FeedError, match="DTD"):
        module.extract_items(document)


def test_feed_item_count_is_bounded():
    document = "<rss><channel>" + "<item><title>x</title></item>" * (module.MAX_ITEMS + 1) + "</channel></rss>"
    with pytest.raises(module.FeedError, match="too many"):
        module.extract_items(document.encode())


def test_proxy_options_are_removed():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "--proxy" not in source
    assert "ProxyHandler" not in source


def test_html_and_control_characters_are_bounded():
    assert module.clean_text("<b>Hello</b>\nworld\x00") == "Hello world"
    assert len(module.clean_text("x" * 5000)) == module.MAX_TEXT_LENGTH
