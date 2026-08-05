"""Regression tests for Checkmk secret-aware command arguments."""
import ast
from pathlib import Path
SOURCE = Path(__file__).parents[1] / 'src/sap_cloud_alm/server_side_calls/agent_sap_alm.py'
def test_server_side_call_preserves_secret_object() -> None:
    text = SOURCE.read_text(encoding='utf-8'); tree = ast.parse(text)
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'unsafe' for node in ast.walk(tree))
    assert 'Secret' in text
