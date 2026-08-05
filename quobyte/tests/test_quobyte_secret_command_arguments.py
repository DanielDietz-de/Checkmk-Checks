"""Regression tests for Quobyte secret and TLS command boundaries."""

from __future__ import annotations

import ast
import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SERVER_SIDE_CALL = PACKAGE_ROOT / "src/quobyte/server_side_calls/quobyte.py"
RULESET = PACKAGE_ROOT / "src/quobyte/rulesets/agent.py"
AGENT = PACKAGE_ROOT / "src/quobyte/libexec/agent_quobyte"


def _load_agent():
    loader = importlib.machinery.SourceFileLoader("quobyte_agent_test", str(AGENT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_server_side_call_preserves_secret_object() -> None:
    text = SERVER_SIDE_CALL.read_text(encoding="utf-8")
    tree = ast.parse(text)
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "unsafe"
        for node in ast.walk(tree)
    )
    assert "Secret" in text


def test_ca_bundle_flows_from_ruleset_to_agent() -> None:
    server_source = SERVER_SIDE_CALL.read_text(encoding="utf-8")
    ruleset_source = RULESET.read_text(encoding="utf-8")
    agent_source = AGENT.read_text(encoding="utf-8")

    assert "ca_file: str | None = None" in server_source
    assert '"--ca-file"' in server_source
    assert '"ca_file": DictElement(' in ruleset_source
    assert 'parser.add_argument(\n        "--ca-file"' in agent_source
    assert 'os.environ.get("REQUESTS_CA_BUNDLE")' in agent_source
    assert 'os.environ.get("CURL_CA_BUNDLE")' in agent_source


def test_requests_ca_bundle_is_preserved_without_proxy_inheritance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load_agent()
    bundle = tmp_path / "site-ca.pem"
    bundle.write_text("test CA bundle\n", encoding="utf-8")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(bundle))
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:8080")

    client = module.Quobyte("https://quobyte.invalid", "user", "secret", 5.0)

    assert client.session.trust_env is False
    assert client.session.verify == str(bundle.resolve())


def test_curl_ca_bundle_is_the_compatible_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load_agent()
    bundle = tmp_path / "curl-ca.pem"
    bundle.write_text("test CA bundle\n", encoding="utf-8")
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.setenv("CURL_CA_BUNDLE", str(bundle))

    client = module.Quobyte("https://quobyte.invalid", "user", "secret", 5.0)

    assert client.session.verify == str(bundle.resolve())


def test_explicit_ca_bundle_overrides_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load_agent()
    environment_bundle = tmp_path / "environment-ca.pem"
    explicit_bundle = tmp_path / "explicit-ca.pem"
    environment_bundle.write_text("environment CA\n", encoding="utf-8")
    explicit_bundle.write_text("explicit CA\n", encoding="utf-8")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(environment_bundle))

    client = module.Quobyte(
        "https://quobyte.invalid",
        "user",
        "secret",
        5.0,
        str(explicit_bundle),
    )

    assert client.session.verify == str(explicit_bundle.resolve())


def test_missing_ca_bundle_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _load_agent()
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("CURL_CA_BUNDLE", raising=False)

    with pytest.raises(ValueError, match="CA bundle does not exist"):
        module.Quobyte(
            "https://quobyte.invalid",
            "user",
            "secret",
            5.0,
            str(tmp_path / "missing.pem"),
        )
