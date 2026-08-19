"""Transport regression tests for ADFS certificate collection."""

import ast
from pathlib import Path


AGENT = Path(__file__).parents[1] / "src/adfs_certificates/libexec/agent_adfs_certificates"


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


def test_tls_verification_is_not_disabled_unconditionally() -> None:
    """Verify that tls verification is not disabled unconditionally."""
    tree = ast.parse(AGENT.read_text(encoding="utf-8"))
    assert not any(
        isinstance(node, ast.keyword)
        and node.arg == "verify"
        and isinstance(node.value, ast.Constant)
        and node.value.value is False
        for node in ast.walk(tree)
    )
