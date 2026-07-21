import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "src" / "notifications" / "rediscover_service"
loader = SourceFileLoader("rediscover_service", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)


def _snapshot(etag, *changes):
    return module.PendingChanges(etag=etag, changes=tuple(changes))


def _change(
    change_id,
    *,
    user="automation",
    text="Refreshed services on switch1",
    action="refresh-autochecks",
):
    return {
        "id": change_id,
        "user_id": user,
        "text": text,
        "action_name": action,
    }


def test_accepts_current_site_on_loopback(monkeypatch):
    monkeypatch.setenv("OMD_SITE", "cmk")
    assert module.local_api_url("http", "127.0.0.1:5000", "cmk") == (
        "http://127.0.0.1:5000/cmk/check_mk/api/1.0"
    )


def test_rejects_remote_host_before_reading_secret(monkeypatch):
    monkeypatch.setenv("OMD_SITE", "cmk")
    with pytest.raises(module.UnsafeSiteTarget, match="loopback"):
        module.local_api_url("https", "monitoring.example", "cmk")


def test_rejects_other_site(monkeypatch):
    monkeypatch.setenv("OMD_SITE", "cmk")
    with pytest.raises(module.UnsafeSiteTarget, match="local site"):
        module.local_api_url("http", "localhost", "other")


def test_only_problem_service_notifications_are_eligible(monkeypatch):
    monkeypatch.setenv("NOTIFY_WHAT", "SERVICE")
    monkeypatch.setenv("NOTIFY_NOTIFICATIONTYPE", "PROBLEM")
    monkeypatch.setenv("NOTIFY_SERVICESTATE", "CRIT")
    assert module.notification_is_eligible()

    monkeypatch.setenv("NOTIFY_NOTIFICATIONTYPE", "RECOVERY")
    assert not module.notification_is_eligible()

    monkeypatch.setenv("NOTIFY_NOTIFICATIONTYPE", "PROBLEM")
    monkeypatch.setenv("NOTIFY_SERVICESTATE", "OK")
    assert not module.notification_is_eligible()


def test_refuses_preexisting_automation_changes():
    before = _snapshot("one", _change("old"))
    with pytest.raises(module.RediscoveryError, match="already has pending changes"):
        module.ensure_clean_automation_scope(before, "automation")


def test_accepts_only_new_owned_changes_for_expected_host():
    before = _snapshot(
        "one",
        _change("foreign-old", user="admin", text="Updated another host"),
    )
    after = _snapshot(
        "two",
        *before.changes,
        _change("new", text="Refreshed services on switch1"),
    )
    assert module.verify_new_automation_changes(
        before,
        after,
        "automation",
        "switch1",
    ) == {"new"}


def test_rejects_concurrent_foreign_change():
    before = _snapshot("one")
    after = _snapshot(
        "two",
        _change("ours"),
        _change("other", user="admin", text="Updated switch2"),
    )
    with pytest.raises(module.RediscoveryError, match="concurrent or unrelated"):
        module.verify_new_automation_changes(
            before,
            after,
            "automation",
            "switch1",
        )


def test_rejects_same_user_change_for_other_host():
    before = _snapshot("one")
    after = _snapshot(
        "two",
        _change("ours"),
        _change("other", text="Updated switch2"),
    )
    with pytest.raises(module.RediscoveryError, match="concurrent or unrelated"):
        module.verify_new_automation_changes(
            before,
            after,
            "automation",
            "switch1",
        )


class _ActivationResponse:
    status_code = 204
    text = ""


class _ActivationSession:
    def __init__(self):
        self.kwargs = None

    def post(self, *_args, **kwargs):
        self.kwargs = kwargs
        return _ActivationResponse()


def test_activation_is_site_scoped_and_never_forced():
    session = _ActivationSession()
    module.activate_changes(
        session,
        "http://localhost/cmk/check_mk/api/1.0",
        "cmk",
        _snapshot("etag"),
    )
    assert session.kwargs["headers"]["If-Match"] == "etag"
    assert session.kwargs["json"]["sites"] == ["cmk"]
    assert session.kwargs["json"]["force_foreign_changes"] is False
    assert session.kwargs["allow_redirects"] is False
