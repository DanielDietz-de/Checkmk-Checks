"""Package-local structural and transport tests for the Pure integration."""

from __future__ import annotations

import ast
import json
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src"
README = PACKAGE_ROOT / "README.md"
AGENT = SOURCE_ROOT / "pure/libexec/agent_pure"


def _is_python_source(path: Path) -> bool:
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


def _flasharray_constructor() -> ast.Call:
    tree = ast.parse(AGENT.read_text(encoding="utf-8"), filename=str(AGENT))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if (
            isinstance(node.func.value, ast.Name)
            and node.func.value.id == "purestorage"
            and node.func.attr == "FlashArray"
        ):
            return node
    raise AssertionError("purestorage.FlashArray constructor was not found")


def test_flasharray_uses_dedicated_tls_parameters() -> None:
    """TLS verification must not be mixed into generic request keyword arguments."""
    call = _flasharray_constructor()
    keywords = {keyword.arg: keyword.value for keyword in call.keywords}

    assert "verify_https" in keywords
    assert "ssl_cert" in keywords
    request_kwargs = keywords["request_kwargs"]
    assert isinstance(request_kwargs, ast.Dict)
    keys = {
        key.value
        for key in request_kwargs.keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }
    assert keys == {"timeout"}
    assert "verify" not in keys


def test_agent_validates_the_flasharray_client_contract() -> None:
    """Unsupported client releases must fail clearly before a network request."""
    source = AGENT.read_text(encoding="utf-8")
    assert "_validate_purestorage_client()" in source
    assert '{"verify_https", "ssl_cert", "request_kwargs"}' in source
    assert "purestorage==1.19.0" in source


def test_tls_cli_options_are_mutually_exclusive() -> None:
    """A CA bundle and disabled verification must not be accepted together."""
    source = AGENT.read_text(encoding="utf-8")
    assert "tls_group = parser.add_mutually_exclusive_group()" in source
    assert 'tls_group.add_argument(\n        "--ca-file"' in source
    assert 'tls_group.add_argument(\n        "--no-cert-check"' in source
