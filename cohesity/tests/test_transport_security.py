"""Regression tests for the special agent transport policy."""

import ast
from pathlib import Path

SOURCE = Path(__file__).parents[1] / 'src/cohesity/libexec/agent_cohesity'


def test_source_has_no_global_tls_warning_suppression() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    assert "disable_warnings" not in text
    assert "InsecureRequestWarning" not in text
    ast.parse(text)
