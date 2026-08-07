"""Static compatibility contracts for S2D/HCI Checkmk API definitions."""

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
GRAPHING_PLUGIN = PACKAGE_ROOT / "src/s2d_hci/graphing/graphing_s2d_hci.py"
RULESET_PLUGINS = (
    PACKAGE_ROOT / "src/s2d_hci/rulesets/ruleset_s2d_hci.py",
    PACKAGE_ROOT / "src/s2d_hci/rulesets/ruleset_s2d_hci_workloads.py",
)


def test_graphing_titles_use_localizable_title_objects():
    """Require Checkmk 2.5-compatible Title wrappers for metrics and graphs."""

    text = GRAPHING_PLUGIN.read_text(encoding="utf-8")
    assert "from cmk.graphing.v1 import Title" in text
    assert 'title="' not in text
    assert text.count("title=Title(") == 14


def test_ruleset_level_prefills_use_default_value_objects():
    """Require form-spec wrappers that Checkmk can deserialize during validation."""

    combined = "\n".join(path.read_text(encoding="utf-8") for path in RULESET_PLUGINS)
    assert "DefaultValue" in combined
    assert "prefill_fixed_levels=(" not in combined
    assert combined.count("prefill_fixed_levels=DefaultValue(value=(") == 4
