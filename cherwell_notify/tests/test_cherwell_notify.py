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

MODULE_PATH = Path(__file__).parents[1] / "src" / "notifications" / "cherwell_notify"
loader = SourceFileLoader("cherwell_notify", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)


def base_context(**overrides):
    context = {
        "PARAMETER_API_URL": "https://cherwell.example/api/businessobject",
        "PARAMETER_TOKEN_URL": "https://cherwell.example/token",
        "PARAMETER_CLIENT_ID": "client",
        "PARAMETER_USERNAME": "user",
        "PARAMETER_PASSWORD": "password",
        "PARAMETER_AUTOMATION_SECRET": "automation-secret",
        "PARAMETER_BUSINESS_OBJECT_ID": "incident-object",
        "PARAMETER_DESCRIPTION_FIELD_ID": "description-field",
        "PARAMETER_INSERT_FIELDS_JSON": "[]",
        "PARAMETER_UPDATE_FIELDS_JSON": "[]",
        "PARAMETER_CACHE_SCOPE": "Tenant",
        "PARAMETER_RECOVERY_MODE": "ignore",
        "PARAMETER_TIMEOUT": "10",
        "PARAMETER_CMK_SERVER": "monitoring.example",
        "PARAMETER_CMK_SITE": "cmk",
        "NOTIFICATIONTYPE": "PROBLEM",
        "WHAT": "SERVICE",
        "HOSTNAME": "host1",
        "SERVICEDESC": "CPU load",
        "SERVICESTATE": "CRIT",
        "SERVICEOUTPUT": "load high",
    }
    context.update(overrides)
    return context


def test_rejects_cleartext_and_embedded_credentials():
    with pytest.raises(module.CherwellError, match="HTTPS"):
        module.validate_https_url("http://cherwell.example/api", "API URL")
    with pytest.raises(module.CherwellError, match="embedded credentials"):
        module.validate_https_url("https://user:pass@cherwell.example/api", "API URL")


def test_field_mapping_parser_is_bounded_and_normalized():
    fields = module.parse_field_mappings(
        '[{"fieldId":"field-1","value":42,"dirty":false}]',
        "fields",
    )
    assert fields == [{"dirty": False, "fieldId": "field-1", "value": "42"}]


def test_event_id_is_initialized_when_context_has_no_ec_event():
    notification = module.NotifyCherwell(base_context())
    assert notification.event_id is None


def test_recovery_ignore_does_not_authenticate(monkeypatch):
    notification = module.NotifyCherwell(
        base_context(NOTIFICATIONTYPE="RECOVERY")
    )
    monkeypatch.setattr(
        notification,
        "get_login_token",
        lambda: pytest.fail("recovery ignore must not request a token"),
    )
    assert notification.notify() == 0


def test_payload_uses_configured_business_object_and_fields():
    notification = module.NotifyCherwell(
        base_context(
            PARAMETER_INSERT_FIELDS_JSON='[{"fieldId":"tenant-field","value":"tenant-value"}]'
        )
    )
    payload = notification.build_insert_payload()
    assert payload["busObId"] == "incident-object"
    assert [field["fieldId"] for field in payload["fields"]] == [
        "description-field",
        "tenant-field",
    ]


def test_checkmk_server_cannot_contain_a_path():
    with pytest.raises(module.CherwellError, match="must not contain a path"):
        module.NotifyCherwell(base_context(PARAMETER_CMK_SERVER="monitoring.example/site"))
