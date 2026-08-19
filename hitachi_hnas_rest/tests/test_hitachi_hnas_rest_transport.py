"""Regression tests for Hitachi HNAS transport and private-CA handling."""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
AGENT = PACKAGE_ROOT / "src/hitachi_hnas_rest/libexec/agent_hitachi_hnas_rest"
SERVER_SIDE = PACKAGE_ROOT / "src/hitachi_hnas_rest/server_side_calls/agent.py"
RULESET = PACKAGE_ROOT / "src/hitachi_hnas_rest/rulesets/agent.py"


def _load_agent():
    """Handle load agent for this module's workflow."""
    loader = importlib.machinery.SourceFileLoader("hitachi_hnas_agent_test", str(AGENT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_ca_bundle_flows_from_ruleset_to_agent() -> None:
    """Verify that ca bundle flows from ruleset to agent."""
    server_source = SERVER_SIDE.read_text(encoding="utf-8")
    ruleset_source = RULESET.read_text(encoding="utf-8")
    agent_source = AGENT.read_text(encoding="utf-8")

    assert 'params.get("ca_file")' in server_source
    assert '"--ca-file"' in server_source
    assert '"ca_file": DictElement(' in ruleset_source
    assert 'parser.add_argument("--ca-file"' in agent_source
    assert 'os.environ.get("REQUESTS_CA_BUNDLE")' in agent_source
    assert 'os.environ.get("CURL_CA_BUNDLE")' in agent_source


def test_requests_ca_bundle_is_preserved_with_proxy_isolation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify that requests ca bundle is preserved with proxy isolation."""
    module = _load_agent()
    bundle = tmp_path / "site-ca.pem"
    bundle.write_text("site CA\n", encoding="utf-8")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(bundle))
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:8080")

    agent = module.AgentHitachiHnasRest(
        SimpleNamespace(
            host_address="hnas.example.test",
            port=8444,
            timeout=30,
            ca_file=None,
            no_cert_check=False,
            api_key="test-key",
            user=None,
            password=None,
        )
    )

    assert agent.verify == str(bundle.resolve())
    assert agent.session.trust_env is False


def test_curl_ca_bundle_is_the_compatible_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify that curl ca bundle is the compatible fallback."""
    module = _load_agent()
    bundle = tmp_path / "curl-ca.pem"
    bundle.write_text("curl CA\n", encoding="utf-8")
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.setenv("CURL_CA_BUNDLE", str(bundle))

    assert module._resolve_ca_bundle(None, False) == str(bundle.resolve())


def test_explicit_ca_bundle_overrides_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify that explicit ca bundle overrides environment."""
    module = _load_agent()
    environment_bundle = tmp_path / "environment.pem"
    explicit_bundle = tmp_path / "explicit.pem"
    environment_bundle.write_text("environment CA\n", encoding="utf-8")
    explicit_bundle.write_text("explicit CA\n", encoding="utf-8")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(environment_bundle))

    assert module._resolve_ca_bundle(str(explicit_bundle), False) == str(
        explicit_bundle.resolve()
    )


def test_tls_opt_out_is_explicit_and_conflicts_are_rejected(tmp_path: Path) -> None:
    """Verify that tls opt out is explicit and conflicts are rejected."""
    module = _load_agent()
    bundle = tmp_path / "private.pem"
    bundle.write_text("private CA\n", encoding="utf-8")

    assert module._resolve_ca_bundle(None, True) is False
    with pytest.raises(ValueError, match="mutually exclusive"):
        module._resolve_ca_bundle(str(bundle), True)


def test_missing_ca_bundle_is_rejected(tmp_path: Path) -> None:
    """Verify that missing ca bundle is rejected."""
    module = _load_agent()
    with pytest.raises(ValueError, match="CA bundle does not exist"):
        module._resolve_ca_bundle(str(tmp_path / "missing.pem"), False)
