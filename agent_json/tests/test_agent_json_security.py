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
    def __init__(self, status=200, payload=None, headers=None, redirect=False):
        self.status_code = status
        self.headers = headers or {}
        self.is_redirect = redirect
        self._body = json.dumps(payload).encode() if payload is not None else b""

    def iter_content(self, chunk_size=65536):
        yield self._body


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []
        self.trust_env = True

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.response


def endpoint(url="https://health.example/status"):
    return module.Endpoint(url=url, username="user", password="secret", method="GET")


def test_rejects_http_and_embedded_credentials():
    with pytest.raises(module.EndpointError, match="HTTPS"):
        module.AgentJson.validate_url("http://health.example/status")
    with pytest.raises(module.EndpointError, match="embedded credentials"):
        module.AgentJson.validate_url("https://user:pass@health.example/status")


def test_request_is_verified_bounded_and_does_not_follow_redirects():
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
    agent = module.AgentJson([endpoint()])
    agent.session = FakeSession(FakeResponse(status=401, payload={"secret": "leak"}))
    with pytest.raises(module.EndpointError) as exc:
        agent.fetch_checks(endpoint())
    assert "leak" not in str(exc.value)
    assert "401" in str(exc.value)


def test_service_name_and_output_cannot_inject_local_checks():
    name = 'bad"\n2 "Injected"'
    safe_name = module.AgentJson.safe_service_name(name)
    output = module.AgentJson.check_output(
        {"summary": "first\n2 injected", "data": {"x\r\n": "value\x00"}}
    )
    assert "\n" not in safe_name
    assert "\n" not in output
    assert '\\"' in safe_name


def test_schema_rejects_non_list_checks():
    agent = module.AgentJson([endpoint()])
    agent.session = FakeSession(FakeResponse(payload={"checks": {}}))
    with pytest.raises(module.EndpointError, match="checks list"):
        agent.fetch_checks(endpoint())


def test_malformed_argument_groups_fail_closed(capsys):
    assert module.main(["https://health.example", "user"]) == 1
    output = capsys.readouterr().out
    assert "<<<local>>>" in output
    assert "configuration" in output
