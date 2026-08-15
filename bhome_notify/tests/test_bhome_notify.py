import ast
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

PACKAGE_ROOT = Path(__file__).parents[1]
MODULE_PATH = PACKAGE_ROOT / "src" / "notifications" / "bhome_notify"
RULESET_PATH = (
    PACKAGE_ROOT
    / "src"
    / "bhome_notify"
    / "rulesets"
    / "notification_parameter.py"
)
loader = SourceFileLoader("bhome_notify", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)


class Response:
    """Represent response behavior and associated state."""
    status_code = 200
    is_redirect = False
    headers = {}

    def __init__(self, payload):
        """Initialize the instance and its required state."""
        self.body = json.dumps(payload).encode()

    def iter_content(self, chunk_size=65536):
        """Handle iter content for this module's workflow."""
        yield self.body


class Session:
    """Represent session behavior and associated state."""
    def __init__(self, response=None, error=None):
        """Initialize the instance and its required state."""
        self.response = response
        self.error = error
        self.calls = []
        self.trust_env = True

    def post(self, url, **kwargs):
        """Handle post for this module's workflow."""
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


def config():
    """Handle config for this module's workflow."""
    return {
        "portal_domain": "helix.example",
        "tenant_id": "tenant",
        "access": "access",
        "secret": "secret",
        "timeout": 10,
        "verify": True,
    }


def test_portal_domain_is_https_and_has_fixed_path():
    """Verify that portal domain is https and has fixed path."""
    assert module.validate_portal_domain("helix.example:443") == (
        "https://helix.example:443/events-service/api/v1.0/events"
    )
    with pytest.raises(module.HelixNotificationError):
        module.validate_portal_domain("https://helix.example/path")


def test_uses_native_api_key_without_auth_module():
    """Verify that uses native api key without auth module."""
    session = Session(Response({"statusCode": "200", "successfullEventIds": ["e1"]}))
    assert module.send_event([{"class": "checkmk_ev"}], config(), session=session) == 0
    _, kwargs = session.calls[0]
    assert kwargs["headers"]["Authorization"] == "apiKey tenant::access::secret"
    assert kwargs["allow_redirects"] is False
    assert kwargs["verify"] is True
    assert session.trust_env is False


def test_ambiguous_transport_error_is_not_retried():
    """Verify that ambiguous transport error is not retried."""
    session = Session(error=module.requests.Timeout("timeout"))
    with pytest.raises(module.HelixNotificationError, match="request failed"):
        module.send_event([{"class": "checkmk_ev"}], config(), session=session)
    assert len(session.calls) == 1


def test_payload_uses_stable_problem_identifier_for_service():
    """Verify that payload uses stable problem identifier for service."""
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
    """Verify that api level failure is rejected."""
    response = Response({"statusCode": "400", "statusMsg": "Rejected"})
    with pytest.raises(module.HelixNotificationError, match="Rejected"):
        module.validate_api_response(response, response.body)


def test_lowercase_api_success_status_is_accepted():
    """Verify that lowercase api success status is accepted."""
    response = Response({"status": "success", "successfullEventIds": ["e1"]})
    assert module.validate_api_response(response, response.body)["status"] == "success"


def test_package_metadata_representations_match():
    """Verify that package metadata representations match."""
    python_info = ast.literal_eval(
        (PACKAGE_ROOT / "src" / "info").read_text(encoding="utf-8")
    )
    json_info = json.loads(
        (PACKAGE_ROOT / "src" / "info.json").read_text(encoding="utf-8")
    )
    assert python_info == json_info


def test_timeout_form_is_optional_and_matches_runtime_bounds():
    """Verify that timeout form is optional and matches runtime bounds."""
    source = RULESET_PATH.read_text(encoding="utf-8")
    timeout_block = source.split('"timeout": DictElement(', 1)[1].split(
        '"ca_bundle": DictElement(', 1
    )[0]
    assert "required=False" in timeout_block
    assert "NumberInRange(min_value=0.5, max_value=120.0)" in timeout_block
