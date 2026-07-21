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

MODULE_PATH = Path(__file__).parents[1] / "src" / "notifications" / "service_now_notify"
loader = SourceFileLoader("service_now_notify", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)


class Response:
    status_code = 204
    is_redirect = False
    headers = {}

    def iter_content(self, chunk_size=65536):
        yield b""


class Session:
    def __init__(self, error=None):
        self.error = error
        self.calls = []
        self.trust_env = True

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return Response()


def test_base_url_requires_https_and_normalizes_slash():
    assert module.validate_base_url("https://snow.example/api") == "https://snow.example/api/"
    with pytest.raises(module.ServiceNowError, match="HTTPS"):
        module.validate_base_url("http://snow.example/api")


def test_problem_and_recovery_use_safe_url_joining():
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
    groups = "SNOW_bad,SNOW_010_OS,other,SNOW_200_APP"
    assert module.choose_assignment_group(groups) == "SNOW_200_APP"


def test_correct_service_override_key_has_precedence():
    assert module.service_assignment_override(
        {
            "SERVICE_SNOW_RESP_GRP_2": "new",
            "SERVICE_SVC_SNOW_RESP_GRP_2": "legacy",
        }
    ) == "new"


def test_recovery_payload_uses_same_source_identifier_logic():
    context = {
        "WHAT": "SERVICE",
        "OMD_SITE": "cmk",
        "HOSTNAME": "host1",
        "SERVICEDESC": "CPU",
    }
    assert module.build_recovery_payload(context)["QUELLEID"] == "cmk|host1|CPU"
