"""Static compatibility contracts for S2D/HCI Graphing API definitions."""

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
GRAPHING_PLUGIN = PACKAGE_ROOT / "src/s2d_hci/graphing/graphing_s2d_hci.py"


def test_graphing_titles_use_localizable_title_objects():
    """Require Checkmk 2.5-compatible Title wrappers for metrics and graphs."""

    text = GRAPHING_PLUGIN.read_text(encoding="utf-8")
    assert "from cmk.graphing.v1 import Title" in text
    assert 'title="' not in text
    assert text.count("title=Title(") == 14
