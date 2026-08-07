"""Static Checkmk Graphing and Rulesets API contract tests."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_graphing_titles_use_localizable_title_objects() -> None:
    """Metric and graph titles must use Checkmk's localizable `Title` wrapper."""

    text = (ROOT / "src/s2d_hci/graphing/graphing_s2d_hci.py").read_text(encoding="utf-8")
    assert 'title="' not in text
    assert text.count("title=Title(") >= 14


def test_simple_levels_use_default_value_wrapper() -> None:
    """Checkmk 2.5 `SimpleLevels` prefills must be wrapped in `DefaultValue`."""

    text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "src/s2d_hci/rulesets/ruleset_s2d_hci.py",
            "src/s2d_hci/rulesets/ruleset_s2d_hci_workloads.py",
        )
    )
    assert not re.search(r"prefill_fixed_levels\s*=\s*\(", text)
    assert "prefill_fixed_levels=DefaultValue(value=" in text
