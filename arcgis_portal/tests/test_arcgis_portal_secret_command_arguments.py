"""Regression tests for ArcGIS secret handling and safe diagnostics."""

import ast
from pathlib import Path


PACKAGE = Path(__file__).parents[1]
AGENT = PACKAGE / "src/arcgis_portal/libexec/agent_arcgis_portal"
SERVER = PACKAGE / "src/arcgis_portal/server_side_calls/agent.py"
RULESET = PACKAGE / "src/arcgis_portal/rulesets/agent.py"


def test_server_side_call_preserves_secret_object() -> None:
    text = SERVER.read_text(encoding="utf-8")
    tree = ast.parse(text)
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "unsafe"
        for node in ast.walk(tree)
    )
    assert "Secret" in text
    assert '"--password-id"' in text


def test_agent_resolves_password_store_reference() -> None:
    text = AGENT.read_text(encoding="utf-8")
    assert "cmk.utils.password_store" in text
    assert '"--password-id"' in text
    assert "_resolve_secret_reference" in text


def test_debug_output_excludes_bodies_and_query_secrets() -> None:
    text = AGENT.read_text(encoding="utf-8")
    tree = ast.parse(text)
    debug = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_debug"
    )
    rendered = ast.unparse(debug)
    assert ".text" not in rendered
    assert "_safe_request_url" in rendered
    assert "response_bytes" in rendered
    rules = RULESET.read_text(encoding="utf-8")
    assert "raw responses" not in rules
    rule_messages = " ".join(
        node.value
        for node in ast.walk(ast.parse(rules))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
    )
    assert "response bodies and credentials are excluded" in rule_messages
