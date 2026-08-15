"""Regression coverage for literal-aware function documentation scanning."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_policy_tool():
    """Load the permanent documentation checker for lexical regression tests."""
    path = Path("tools/ci/check_function_documentation.py")
    spec = importlib.util.spec_from_file_location("check_function_documentation", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_normalizer_tool():
    """Load the documentation normalizer with its policy module available."""
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


def _findings(module, tmp_path, monkeypatch, name: str, source_text: str) -> list[str]:
    """Return policy findings for one temporary source file."""
    source = tmp_path / name
    source.write_text(source_text, encoding="utf-8")
    monkeypatch.setattr(module, "tracked_files", lambda _root: [source])
    return module.collect_findings(tmp_path)


def test_shell_heredoc_function_shape_is_ignored(tmp_path, monkeypatch) -> None:
    """Verify shell heredoc bodies cannot create fake function declarations."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "helper.sh",
        "#!/bin/bash\n"
        "cat <<'EOF'\n"
        "function generated_helper() {\n"
        "EOF\n"
        "# Run the actual helper task safely.\n"
        "real_helper() { :; }\n",
    )
    assert findings == []


def test_shell_multiline_quote_function_shape_is_ignored(tmp_path, monkeypatch) -> None:
    """Verify multiline shell quotes cannot create fake function declarations."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "helper.sh",
        "#!/bin/bash\n"
        "example='first line\n"
        "function generated_helper() {\n"
        "last line'\n"
        "# Run the actual helper task safely.\n"
        "real_helper() { :; }\n",
    )
    assert findings == []


def test_shell_normalizer_ignores_heredoc_function_shape(tmp_path, monkeypatch) -> None:
    """Verify shell normalization ignores function-shaped heredoc content."""
    module = _load_normalizer_tool()
    source = tmp_path / "helper.sh"
    source.write_text(
        "#!/bin/bash\ncat <<'EOF'\nfunction generated_helper() {\nEOF\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module.policy, "tracked_files", lambda _root: [source])
    counts = module.normalize_repository(tmp_path)
    assert counts["shell"] == 0


def test_powershell_here_string_function_shape_is_ignored(tmp_path, monkeypatch) -> None:
    """Verify PowerShell here-strings cannot create fake function declarations."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "helper.ps1",
        '$example = @"\n'
        "function Generated-Helper { }\n"
        '"@\n'
        "# Run the actual helper task safely.\n"
        "function Invoke-RealHelper { }\n",
    )
    assert findings == []


def test_powershell_block_comment_function_shape_is_ignored(tmp_path, monkeypatch) -> None:
    """Verify PowerShell block comments cannot create fake function declarations."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "helper.ps1",
        "<#\n"
        "function Generated-Helper { }\n"
        "#>\n"
        "# Run the actual helper task safely.\n"
        "function Invoke-RealHelper { }\n",
    )
    assert findings == []


def test_powershell_normalizer_ignores_here_string_function_shape(
    tmp_path, monkeypatch
) -> None:
    """Verify PowerShell normalization ignores function-shaped here-string content."""
    module = _load_normalizer_tool()
    source = tmp_path / "helper.ps1"
    source.write_text(
        '$example = @"\nfunction Generated-Helper { }\n"@\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(module.policy, "tracked_files", lambda _root: [source])
    counts = module.normalize_repository(tmp_path)
    assert counts["powershell"] == 0


def test_php_heredoc_terminator_resumes_same_line_lexing(tmp_path, monkeypatch) -> None:
    """Verify PHP lexing resumes after a same-line heredoc terminator."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "helper.php",
        "<?php\n"
        "$example = <<<TXT\n"
        "embedded text\n"
        "TXT; function undocumented_helper() { return true; }\n",
    )
    assert any(
        "undocumented_helper has no adjacent purpose comment" in item
        for item in findings
    )


def test_php_string_comment_shape_cannot_document_function(tmp_path, monkeypatch) -> None:
    """Verify comment-shaped PHP string text cannot satisfy documentation policy."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "helper.php",
        "<?php\n"
        '$example = "first line\n'
        '// Describe the real function purpose clearly.";\n'
        "function real_helper() { return true; }\n",
    )
    assert any("real_helper has no adjacent purpose comment" in item for item in findings)


def test_php_html_comment_shape_cannot_document_inline_function(tmp_path, monkeypatch) -> None:
    """Verify HTML comment-shaped text cannot document an inline PHP function."""
    module = _load_policy_tool()
    findings = _findings(
        module,
        tmp_path,
        monkeypatch,
        "helper.php",
        "// Describe the real function purpose clearly.\n"
        "<?php function real_helper() { return true; }\n",
    )
    assert any("real_helper has no adjacent purpose comment" in item for item in findings)


def test_php_normalizer_rejects_string_shaped_purpose_comment(
    tmp_path, monkeypatch
) -> None:
    """Verify PHP normalization repairs functions after comment-shaped string text."""
    module = _load_normalizer_tool()
    source = tmp_path / "helper.php"
    source.write_text(
        "<?php\n"
        '$example = "first line\n'
        '// Describe the real function purpose clearly.";\n'
        "function real_helper() { return true; }\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module.policy, "tracked_files", lambda _root: [source])
    counts = module.normalize_repository(tmp_path)
    assert counts["php"] == 1
    assert "// Handle real helper for this source file's runtime workflow." in source.read_text(
        encoding="utf-8"
    )