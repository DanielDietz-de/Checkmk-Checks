import json
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "src" / "agent_json" / "libexec" / "agent_json"
loader = SourceFileLoader("agent_json_runtime", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)


class FakeResponse:
    """Represent fakeresponse behavior and associated state."""
    def __init__(self, status=200, payload=None, headers=None, redirect=False):
        """Initialize the instance and its required state."""
        self.status_code = status
        self.headers = headers or {}
        self.is_redirect = redirect
        self._body = json.dumps(payload).encode() if payload is not None else b""

    def iter_content(self, chunk_size=65536):
        """Handle iter content for this module's workflow."""
        yield self._body


class FakeSession:
    """Represent fakesession behavior and associated state."""
    def __init__(self, response):
        """Initialize the instance and its required state."""
        self.response = response
        self.calls = []
        self.trust_env = True

    def request(self, method, url, **kwargs):
        """Handle request for this module's workflow."""
        self.calls.append((method, url, kwargs))
        return self.response


def endpoint(url="https://health.example/status"):
    """Handle endpoint for this module's workflow."""
    return module.Endpoint(url=url, username="user", password="secret", method="GET")


def test_rejects_http_and_embedded_credentials():
    """Verify that rejects http and embedded credentials."""
    with pytest.raises(module.EndpointError, match="HTTPS"):
        module.AgentJson.validate_url("http://health.example/status")
    with pytest.raises(module.EndpointError, match="embedded credentials"):
        module.AgentJson.validate_url("https://user:pass@health.example/status")


def test_request_is_verified_bounded_and_does_not_follow_redirects():
    """Verify that request is verified bounded and does not follow redirects."""
    agent = module.AgentJson([endpoint()])
    agent.session = FakeSession(
        FakeResponse(payload={"checks": [{"name": "Health", "status": "OK"}]})
    )
    checks = agent.fetch_checks(endpoint())
    assert checks[0]["name"] == "Health"
    _, _, kwargs = agent.session.calls[0]
    assert kwargs["verify"] is True
    assert kwargs["allow_redirects"] is False
    assert kwargs["stream"] is True


def test_http_error_does_not_leak_response_body():
    """Verify that http error does not leak response body."""
    agent = module.AgentJson([endpoint()])
    agent.session = FakeSession(FakeResponse(status=401, payload={"secret": "leak"}))
    with pytest.raises(module.EndpointError) as exc:
        agent.fetch_checks(endpoint())
    assert "leak" not in str(exc.value)
    assert "401" in str(exc.value)


def test_service_name_and_output_cannot_inject_local_checks():
    """Verify that service name and output cannot inject local checks."""
    name = 'bad"\n2 "Injected"'
    safe_name = module.AgentJson.safe_service_name(name)
    output = module.AgentJson.check_output(
        {"summary": "first\n2 injected", "data": {"x\r\n": "value\x00"}}
    )
    assert "\n" not in safe_name
    assert "\n" not in output
    assert '\\"' in safe_name


def test_schema_rejects_non_list_checks():
    """Verify that schema rejects non list checks."""
    agent = module.AgentJson([endpoint()])
    agent.session = FakeSession(FakeResponse(payload={"checks": {}}))
    with pytest.raises(module.EndpointError, match="checks list"):
        agent.fetch_checks(endpoint())


def test_malformed_argument_groups_fail_closed(capsys):
    """Verify that malformed argument groups fail closed."""
    assert module.main(["https://health.example", "user"]) == 1
    output = capsys.readouterr().out
    assert "<<<local>>>" in output
    assert "configuration" in output
