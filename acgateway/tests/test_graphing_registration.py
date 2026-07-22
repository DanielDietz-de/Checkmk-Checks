from pathlib import Path


GRAPHING_FILE = (
    Path(__file__).parents[1]
    / "src"
    / "acgateway"
    / "graphing"
    / "acgateway_extended.py"
)


def test_builtin_active_sessions_metric_is_not_redefined() -> None:
    source = GRAPHING_FILE.read_text(encoding="utf-8")
    assert 'name="active_sessions"' not in source
    assert '"active_sessions"' in source
