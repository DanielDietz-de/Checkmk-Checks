import json
import sys
import types
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

utils = types.ModuleType("cmk.notification_plugins.utils")
utils.collect_context = lambda: {}
utils.get_password_from_env_or_context = lambda key, context: context[key]
notification_plugins = types.ModuleType("cmk.notification_plugins")
notification_plugins.utils = utils
cmk = types.ModuleType("cmk")
cmk.notification_plugins = notification_plugins
sys.modules.setdefault("cmk", cmk)
sys.modules.setdefault("cmk.notification_plugins", notification_plugins)
sys.modules.setdefault("cmk.notification_plugins.utils", utils)

MODULE_PATH = Path(__file__).parents[1] / "src" / "notifications" / "bhome_notify"
loader = SourceFileLoader("bhome_notify", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)


class Response:
    status_code = 200
    is_redirect = False
    headers = {}

    def __init__(self, payload):
        self.body = json.dumps(payload).encode()

    def iter_content(self, chunk_size=65536):
        yield self.body


class Session:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []
        self.trust_env = True

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


def config():
    return {
        "portal_domain": "helix.example",
        "tenant_id": "tenant",
        "access": "access",
        "secret": "secret",
        "timeout": 10,
        "verify": True,
    }


def test_portal_domain_is_https_and_has_fixed_path():
    assert module.validate_portal_domain("helix.example:443") == (
        "https://helix.example:443/events-service/api/v1.0/events"
    )
    with pytest.raises(module.HelixNotificationError):
        module.validate_portal_domain("https://helix.example/path")


def test_uses_native_api_key_without_auth_module():
    session = Session(Response({"statusCode": "200", "successfullEventIds": ["e1"]}))
    assert module.send_event([{"class": "checkmk_ev"}], config(), session=session) == 0
    _, kwargs = session.calls[0]
    assert kwargs["headers"]["Authorization"] == "apiKey tenant::access::secret"
    assert kwargs["allow_redirects"] is False
    assert kwargs["verify"] is True
    assert session.trust_env is False


def test_ambiguous_transport_error_is_not_retried():
    session = Session(error=module.requests.Timeout("timeout"))
    with pytest.raises(module.HelixNotificationError, match="request failed"):
        module.send_event([{"class": "checkmk_ev"}], config(), session=session)
    assert len(session.calls) == 1


def test_payload_uses_stable_problem_identifier_for_service():
    payload = module.build_payload(
        {
            "WHAT": "SERVICE",
            "HOSTNAME": "host.example",
            "SERVICEDESC": "CPU",
            "SERVICESTATE": "CRIT",
            "SERVICEPROBLEMID": "1234",
        }
    )
    assert payload[0]["checkmk_id"] == "1234"
    assert payload[0]["source_identifier"] == "host.example/CPU"


def test_api_level_failure_is_rejected():
    response = Response({"statusCode": "400", "statusMsg": "Rejected"})
    with pytest.raises(module.HelixNotificationError, match="Rejected"):
        module.validate_api_response(response, response.body)
