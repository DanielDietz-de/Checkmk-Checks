import sys
import types
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

utils = types.ModuleType("cmk.notification_plugins.utils")
notification_plugins = types.ModuleType("cmk.notification_plugins")
notification_plugins.utils = utils
cmk = types.ModuleType("cmk")
cmk.notification_plugins = notification_plugins
sys.modules.setdefault("cmk", cmk)
sys.modules.setdefault("cmk.notification_plugins", notification_plugins)
sys.modules.setdefault("cmk.notification_plugins.utils", utils)

MODULE_PATH = Path(__file__).parents[1] / "src" / "notifications" / "kentix"
loader = SourceFileLoader("kentix", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)


class Response:
    status_code = 202
    is_redirect = False


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


def test_gateway_path_is_fixed_and_https():
    assert module.validate_gateway("gateway.example:8443") == (
        "https://gateway.example:8443/php/sms_gateway.php"
    )
    with pytest.raises(module.KentixError, match="HTTPS"):
        module.validate_gateway("http://gateway.example")


def test_sensitive_values_are_in_post_body_not_url():
    session = Session()
    assert module.send_sms(
        gateway="gateway.example",
        key="secret-key",
        pager_number="+49 123 456789",
        text="Critical event",
        timeout=10,
        verify=True,
        session=session,
    ) == 0
    url, kwargs = session.calls[0]
    assert "secret-key" not in url
    assert "+49123456789" not in url
    assert "Critical" not in url
    assert kwargs["data"] == {
        "key": "secret-key",
        "recipients": "+49123456789",
        "message": "Critical event",
    }
    assert kwargs["allow_redirects"] is False
    assert session.trust_env is False


def test_transport_failure_is_not_retried():
    session = Session(error=module.requests.Timeout("timeout"))
    with pytest.raises(module.KentixError, match="request failed"):
        module.send_sms(
            gateway="gateway.example",
            key="key",
            pager_number="+49123456789",
            text="Message",
            timeout=10,
            verify=True,
            session=session,
        )
    assert len(session.calls) == 1


def test_phone_and_message_are_normalized_and_bounded():
    assert module.normalize_pager_number("+49 (123) 456-789") == "+49123456789"
    assert len(module.normalize_message("x" * 500)) == 320
    with pytest.raises(module.KentixError):
        module.normalize_pager_number("not-a-number")
