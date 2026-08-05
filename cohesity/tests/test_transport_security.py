"""Regression tests for the Cohesity special-agent transport and deployment policy."""

import ast
import stat
from pathlib import Path

SOURCE = Path(__file__).parents[1] / "src/cohesity/libexec/agent_cohesity"


def test_source_has_no_global_tls_warning_suppression() -> None:
    """TLS warnings must not be disabled process-wide."""
    text = SOURCE.read_text(encoding="utf-8")
    assert "disable_warnings" not in text
    assert "InsecureRequestWarning" not in text
    ast.parse(text)


def test_special_agent_is_executable() -> None:
    """The packaged libexec entry point must retain its executable mode."""
    assert SOURCE.stat().st_mode & stat.S_IXUSR
