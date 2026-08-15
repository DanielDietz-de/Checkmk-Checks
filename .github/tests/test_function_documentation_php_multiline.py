"""Regression coverage for PHP function declaration lexing and normalization."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_policy_tool():
    """Load the permanent documentation checker for PHP declaration tests."""
    path = Path("tools/ci/check_function_documentation.py")
    spec = importlib.util.spec_from_file_location("check_function_documentation", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_normalizer_tool():
    """Load the documentation normalizer with its sibling policy module available."""
    tool_dir = str(Path("tools/ci").resolve())
    sys.path.insert(0, tool_dir)
    try:
        path = Path("tools/ci/normalize_function_documentation.py")
        spec = importlib.util.spec_from_file_location("normalize_function_documentation", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(tool_dir)


def _findings(module, tmp_path, monkeypatch, source_text: str) -> list[str]:
    """Return policy findings for one temporary PHP source string."""
    source = tmp_path / "helper.php"
    source.write_text(source_text, encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    return module.collect_findings(tmp_path)


def test_multiline_php_function_is_checked(tmp_path, monkeypatch) -> None:
    """Verify a named PHP function split across lines remains policy-visible."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "<?php\nfunction\ncache_path() { return '/tmp'; }\n",
    )
    assert any("cache_path has no adjacent purpose comment" in item for item in findings)


def test_normalizer_documents_multiline_php_function(tmp_path, monkeypatch) -> None:
    """Verify the normalizer documents multiline PHP declarations using shared policy."""
    module = _load_normalizer_tool()
    source = tmp_path / "helper.php"
    source.write_text(
        "<?php\nfunction\ncache_path() { return '/tmp'; }\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module.policy, "tracked_files", lambda _root: [source])
    counts = module.normalize_repository(tmp_path)
    assert counts["php"] == 1
    updated = source.read_text(encoding="utf-8")
    assert "// Handle cache path for this source file's runtime workflow.\nfunction\ncache_path" in updated


def test_php_intertoken_block_comment_is_checked(tmp_path, monkeypatch) -> None:
    """Verify comments between the PHP function keyword and name remain visible."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "<?php\nfunction\n/* generated wrapper */\nrun_task() { return true; }\n",
    )
    assert any("run_task has no adjacent purpose comment" in item for item in findings)


def test_normalizer_documents_php_intertoken_comment(tmp_path, monkeypatch) -> None:
    """Verify normalization shares PHP trivia-aware function matching."""
    module = _load_normalizer_tool()
    source = tmp_path / "helper.php"
    source.write_text(
        "<?php\nfunction /* generated wrapper */ run_task() { return true; }\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module.policy, "tracked_files", lambda _root: [source])
    counts = module.normalize_repository(tmp_path)
    assert counts["php"] == 1
    updated = source.read_text(encoding="utf-8")
    assert (
        "// Handle run task for this source file's runtime workflow.\n"
        "function /* generated wrapper */ run_task"
    ) in updated


def test_php_line_comment_trivia_is_checked(tmp_path, monkeypatch) -> None:
    """Verify PHP line comments are accepted as declaration trivia, not blind spots."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "<?php\npublic /* wrapper */ static function // generated\n& run_task() { return true; }\n",
    )
    assert any("run_task has no adjacent purpose comment" in item for item in findings)


def test_non_ascii_php_function_is_checked(tmp_path, monkeypatch) -> None:
    """Verify PHP identifiers containing non-ASCII characters remain policy-visible."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "<?php\nfunction prüfen() { return true; }\n",
    )
    assert any("prüfen has no adjacent purpose comment" in item for item in findings)


def test_normalizer_documents_non_ascii_php_function(tmp_path, monkeypatch) -> None:
    """Verify normalization handles non-ASCII PHP function names deterministically."""
    module = _load_normalizer_tool()
    source = tmp_path / "helper.php"
    source.write_text("<?php\nfunction prüfen() { return true; }\n", encoding="utf-8")
    monkeypatch.setattr(module.policy, "tracked_files", lambda _root: [source])
    counts = module.normalize_repository(tmp_path)
    assert counts["php"] == 1
    assert "// Handle prüfen for this source file's runtime workflow." in source.read_text(
        encoding="utf-8"
    )


def test_php_block_comment_function_shape_is_ignored(tmp_path, monkeypatch) -> None:
    """Verify function-shaped text inside PHP block comments is never treated as code."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "<?php\n/*\nfunction fake_example() {}\n*/\n// Describe the real function purpose clearly.\nfunction real_example() {}\n",
    )
    assert findings == []


def test_php_quoted_function_shape_is_ignored(tmp_path, monkeypatch) -> None:
    """Verify function-shaped text inside quoted PHP strings is never treated as code."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "<?php\n$example = \"function fake_example() {}\";\n// Describe the real function purpose clearly.\nfunction real_example() {}\n",
    )
    assert findings == []


def test_php_heredoc_function_shape_is_ignored(tmp_path, monkeypatch) -> None:
    """Verify function-shaped text inside PHP heredocs is never treated as code."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "<?php\n$example = <<<JS\nfunction fake_example() {}\nJS;\n// Describe the real function purpose clearly.\nfunction real_example() {}\n",
    )
    assert findings == []


def test_php_nowdoc_function_shape_is_ignored(tmp_path, monkeypatch) -> None:
    """Verify function-shaped text inside PHP nowdocs is never treated as code."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "<?php\n$example = <<<'JS'\nfunction fake_example() {}\nJS;\n// Describe the real function purpose clearly.\nfunction real_example() {}\n",
    )
    assert findings == []


def test_php_anonymous_function_is_ignored(tmp_path, monkeypatch) -> None:
    """Verify anonymous PHP functions remain outside named-symbol documentation policy."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "<?php\n$callback = function /* wrapper */ ($value) { return $value; };\n",
    )
    assert findings == []


def test_php_attribute_preserves_adjacent_purpose_comment(tmp_path, monkeypatch) -> None:
    """Verify PHP attributes remain part of the documented declaration boundary."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "<?php\n// Return the configured route handler value.\n#[Route('/example')]\npublic function route_handler() { return true; }\n",
    )
    assert findings == []


def test_php_slash_comment_closing_tag_returns_to_html(tmp_path, monkeypatch) -> None:
    """Verify a PHP closing tag inside a slash comment ends PHP mode immediately."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "<?php\n// leave PHP mode here ?>\nfunction fake_html_example() {}\n<?php\n// Describe the real function purpose clearly.\nfunction real_example() {}\n",
    )
    assert findings == []


def test_php_hash_comment_closing_tag_returns_to_html(tmp_path, monkeypatch) -> None:
    """Verify a PHP closing tag inside a hash comment ends PHP mode immediately."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "<?php\n# leave PHP mode here ?>\nfunction fake_html_example() {}\n<?php\n// Describe the real function purpose clearly.\nfunction real_example() {}\n",
    )
    assert findings == []