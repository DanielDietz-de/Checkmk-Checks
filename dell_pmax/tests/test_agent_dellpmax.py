import json
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "src" / "dell_pmax" / "libexec" / "agent_dellpmax"
loader = SourceFileLoader("agent_dellpmax", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)


class Response:
    status_code = 200
    is_redirect = False

    def __init__(self, payload):
        self.payload = payload

    def iter_content(self, chunk_size=65536):
        yield json.dumps(self.payload).encode()


class Session:
    def __init__(self, response):
        self.response = response
        self.calls = []
        self.trust_env = True
        self.auth = None
        self.headers = {}

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def agent():
    return module.PmaxAgent(
        address="pmax.example",
        port=8443,
        username="user",
        secret="secret",
        api_version=100,
        timeout=15,
        verify=True,
    )


def test_request_uses_verification_timeout_and_no_redirects():
    instance = agent()
    instance.session = Session(Response({"version": "10"}))
    assert instance.do_get("version") == {"version": "10"}
    _, kwargs = instance.session.calls[0]
    assert kwargs["verify"] is True
    assert kwargs["timeout"] == 15
    assert kwargs["allow_redirects"] is False


def test_api_version_is_not_hardcoded_to_92():
    instance = agent()
    calls = []
    instance.do_get = lambda endpoint: calls.append(endpoint) or {
        "symmetrixId": []
    }
    with pytest.raises(module.PowerMaxError):
        instance.get_local_array_id()
    assert calls == ["100/vvol/symmetrix"]


def test_output_scalar_removes_section_delimiters_and_newlines():
    assert module.PmaxAgent.scalar("bad|value\nnext", "test") == "bad/value next"


def test_ca_bundle_must_be_regular_absolute_file(tmp_path):
    with pytest.raises(SystemExit):
        module.parse_arguments(
            [
                "--address", "pmax",
                "--username", "user",
                "--secret", "secret",
                "--ca-bundle", str(tmp_path / "missing"),
            ]
        )
