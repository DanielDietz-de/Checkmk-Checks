"""Static Agent Bakery deployment contract tests."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_bakery_uses_supported_artifact_types_and_timeouts() -> None:
    """Bakery must deploy direct plug-ins, binaries, and generated config with timeouts."""

    text = (ROOT / "src/lib/python3/cmk/base/cee/plugins/bakery/s2d_hci.py").read_text(encoding="utf-8")
    assert "Plugin(" in text
    assert "SystemBinary(" in text
    assert "PluginConfig(" in text
    assert "OS.WINDOWS" in text
    assert "timeout=timeout" in text
    assert 'register.bakery_plugin(name="s2d_hci"' in text


def test_bakery_rule_keeps_virtualization_opt_in() -> None:
    """The ruleset must present custom Hyper-V collection as disabled by default."""

    text = (ROOT / "src/s2d_hci/rulesets/bakery.py").read_text(encoding="utf-8")
    assert '"virtualization_mode"' in text
    assert 'prefill=DefaultValue("disabled")' in text
