"""Package-local structural and transport tests for the Dell PowerMax integration."""

from __future__ import annotations

import ast
import json
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src"
README = PACKAGE_ROOT / "README.md"
SERVER_SIDE_CALL = SOURCE_ROOT / "dell_pmax/server_side_calls/agent_pmax.py"
RULESET = SOURCE_ROOT / "dell_pmax/rulesets/agent_dellpmax.py"
AGENT = SOURCE_ROOT / "dell_pmax/libexec/agent_dellpmax"


def _is_python_source(path: Path) -> bool:
    """Handle is python source for this module's workflow."""
    if path.suffix == ".py":
        return True
    if path.parent.name == "checks" and path.suffix == "":
        return True
    if path.suffix:
        return False
    try:
        first_line = path.open("r", encoding="utf-8", errors="strict").readline()
    except (OSError, UnicodeError):
        return False
    return "python" in first_line.lower() and first_line.startswith("#!")


def test_canonical_manifest_is_valid() -> None:
    """The source manifest must remain a literal mapping with explicit compatibility fields."""
    manifest = ast.literal_eval((SOURCE_ROOT / "info").read_text(encoding="utf-8"))
    assert isinstance(manifest, dict)
    assert manifest["name"]
    assert manifest["version"]
    assert manifest["version.min_required"]
    assert "version.usable_until" in manifest
    assert isinstance(manifest["files"], dict)


def test_json_manifest_mirror_matches_when_present() -> None:
    """A retained JSON mirror must be an exact rendering of the canonical manifest."""
    mirror = SOURCE_ROOT / "info.json"
    if not mirror.exists():
        return
    manifest = ast.literal_eval((SOURCE_ROOT / "info").read_text(encoding="utf-8"))
    assert json.loads(mirror.read_text(encoding="utf-8")) == manifest


def test_documentation_contains_code_derived_reference() -> None:
    """Operational package documentation must include the generated source inventory."""
    content = README.read_text(encoding="utf-8")
    assert "<!-- code-derived-reference:start -->" in content
    assert "<!-- code-derived-reference:end -->" in content


def test_shipped_python_sources_parse() -> None:
    """Every shipped Python source, including legacy extensionless checks, must parse."""
    for path in sorted(SOURCE_ROOT.rglob("*")):
        if path.is_file() and _is_python_source(path):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_tls_controls_flow_from_ruleset_to_special_agent() -> None:
    """Timeout and TLS controls must flow from the rule to the executable."""
    server_source = SERVER_SIDE_CALL.read_text(encoding="utf-8")
    ruleset_source = RULESET.read_text(encoding="utf-8")
    agent_source = AGENT.read_text(encoding="utf-8")

    assert "timeout: float = 30.0" in server_source
    assert "ca_file: str | None = None" in server_source
    assert "no_cert_check: bool = False" in server_source
    assert '"--timeout"' in server_source
    assert '"--ca-file"' in server_source
    assert '"--no-cert-check"' in server_source
    assert '"timeout": DictElement(' in ruleset_source
    assert '"ca_file": DictElement(' in ruleset_source
    assert '"no_cert_check": DictElement(' in ruleset_source
    assert 'parser.add_argument("--timeout"' in agent_source
    assert 'parser.add_argument("--ca-file"' in agent_source
    assert 'parser.add_argument("--no-cert-check"' in agent_source


def test_contradictory_tls_controls_are_rejected() -> None:
    """The parameter model must reject simultaneous CA and verification opt-out settings."""
    source = SERVER_SIDE_CALL.read_text(encoding="utf-8")
    assert '@model_validator(mode="after")' in source
    assert "ca_file and no_cert_check are mutually exclusive" in source
