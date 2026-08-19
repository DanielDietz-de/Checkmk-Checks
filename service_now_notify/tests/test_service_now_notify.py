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
MODULE_PATH = PACKAGE_ROOT / "src" / "notifications" / "service_now_notify"
RULESET_PATH = (
    PACKAGE_ROOT
    / "src"
    / "service_now_notify"
    / "rulesets"
    / "service_now_notify.py"
)
loader = SourceFileLoader("service_now_notify", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)


class Response:
    """Represent response behavior and associated state."""
    status_code = 204
    is_redirect = False
    headers = {}

    def iter_content(self, chunk_size=65536):
        """Handle iter content for this module's workflow."""
        yield b""


class Session:
    """Represent session behavior and associated state."""
    def __init__(self, error=None):
        """Initialize the instance and its required state."""
        self.error = error
        self.calls = []
        self.trust_env = True

    def post(self, url, **kwargs):
        """Handle post for this module's workflow."""
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return Response()


def test_base_url_requires_https_and_normalizes_slash():
    """Verify that base url requires https and normalizes slash."""
    assert module.validate_base_url("https://snow.example/api") == "https://snow.example/api/"
    with pytest.raises(module.ServiceNowError, match="HTTPS"):
        module.validate_base_url("http://snow.example/api")


def test_problem_and_recovery_use_safe_url_joining():
    """Verify that problem and recovery use safe url joining."""
    session = Session()
    assert module.deliver(
        base_url="https://snow.example/api/",
        endpoint="checkmk/incident/close",
        payload={"FUNKTION": "close"},
        user="user",
        password="secret",
        timeout=15,
        verify=True,
        proxies={},
        session=session,
    ) == 0
    url, kwargs = session.calls[0]
    assert url == "https://snow.example/api/checkmk/incident/close"
    assert kwargs["allow_redirects"] is False
    assert kwargs["verify"] is True
    assert session.trust_env is False


def test_non_idempotent_request_is_not_retried():
    """Verify that non idempotent request is not retried."""
    session = Session(error=module.requests.Timeout("timeout"))
    with pytest.raises(module.ServiceNowError, match="request failed"):
        module.deliver(
            base_url="https://snow.example/api/",
            endpoint="checkmk/incident/create",
            payload={"FUNKTION": "create"},
            user="user",
            password="secret",
            timeout=15,
            verify=True,
            proxies={},
            session=session,
        )
    assert len(session.calls) == 1


def test_assignment_groups_ignore_malformed_values():
    """Verify that assignment groups ignore malformed values."""
    groups = "SNOW_bad,SNOW_010_OS,other,SNOW_200_APP"
    assert module.choose_assignment_group(groups) == "SNOW_200_APP"


def test_correct_service_override_key_has_precedence():
    """Verify that correct service override key has precedence."""
    assert module.service_assignment_override(
        {
            "SERVICE_SNOW_RESP_GRP_2": "new",
            "SERVICE_SVC_SNOW_RESP_GRP_2": "legacy",
        }
    ) == "new"


def test_recovery_payload_uses_same_source_identifier_logic():
    """Verify that recovery payload uses same source identifier logic."""
    context = {
        "WHAT": "SERVICE",
        "OMD_SITE": "cmk",
        "HOSTNAME": "host1",
        "SERVICEDESC": "CPU",
    }
    assert module.build_recovery_payload(context)["QUELLEID"] == "cmk|host1|CPU"


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
