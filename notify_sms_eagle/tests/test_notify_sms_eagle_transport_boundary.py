"""Security regression tests for the SMS Eagle notification transport."""

from pathlib import Path


SOURCE = Path(__file__).parents[1] / "src" / "notifications" / "sms_eagle"
RULESET = (
    Path(__file__).parents[1]
    / "src"
    / "sms_eagle"
    / "rulesets"
    / "notification_parameter.py"
)


def test_notification_transport_is_bounded() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    assert "disable_warnings" not in text
    assert "allow_redirects=False" in text
    assert "trust_env = False" in text
    assert "timeout=REQUEST_TIMEOUT" in text
    assert "stream=True" in text
    assert "MAX_RESPONSE_BYTES" in text


def test_remote_cleartext_requires_explicit_rule_opt_in() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    ruleset = RULESET.read_text(encoding="utf-8")
    assert "allow_insecure_http" in source
    assert '"allow_insecure_http"' in ruleset
    assert "DefaultValue(False)" in ruleset
