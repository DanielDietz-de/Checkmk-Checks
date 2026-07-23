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
    assert module.validate_public_https_url("https://status.example/feed.xml") == "https://status.example/feed.xml"
    monkeypatch.setattr(module.socket, "getaddrinfo", private_dns)
    with pytest.raises(module.FeedError, match="non-public"):
        module.validate_public_https_url("https://internal.example/feed.xml")


def test_rejects_dtd_and_entity_documents():
    with pytest.raises(module.FeedError, match="DTD"):
        module.extract_items(b"<!DOCTYPE rss [<!ENTITY x 'boom'>]><rss></rss>")


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
