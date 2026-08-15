"""Security regression tests for UCP / MKE transport defaults."""

import ast
from pathlib import Path


PACKAGE = Path(__file__).parents[1]
AGENT = PACKAGE / "src/ucp_health/libexec/agent_ucp_health"
SERVER = PACKAGE / "src/ucp_health/server_side_calls/agent.py"
RULESET = PACKAGE / "src/ucp_health/rulesets/agent.py"


def test_tls_verification_is_enabled_by_default() -> None:
    """Verify that tls verification is enabled by default."""
    assert "no_verify_ssl: bool = False" in SERVER.read_text(encoding="utf-8")
    rules = RULESET.read_text(encoding="utf-8")
    assert "prefill=DefaultValue(False)" in rules
    assert "enabled in production" in rules


def test_all_http_requests_have_timeouts() -> None:
    """Verify that all http requests have timeouts."""
    tree = ast.parse(AGENT.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "requests"
        and node.func.attr in {"get", "post", "request"}
    ]
    assert calls
    assert all(any(keyword.arg == "timeout" for keyword in call.keywords) for call in calls)
