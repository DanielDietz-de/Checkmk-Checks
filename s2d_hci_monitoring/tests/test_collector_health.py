"""Collector-health service behavior tests."""

from __future__ import annotations

import json

from cmk.agent_based.v2 import State
from s2d_hci.agent_based.s2d_hci_collector_health import (
    check_s2d_hci_collector_health,
    parse_s2d_hci_collector_health,
)


def _health(**overrides: object) -> list[list[str]]:
    """Return one complete collector-health row with optional overrides."""

    data: dict[str, object] = {
        "protocol_version": 1,
        "run_id": "run-1",
        "collector": "fast",
        "success": True,
        "complete": True,
        "truncated": False,
        "role": "leader",
        "record_count": 4,
        "output_bytes": 100,
        "elapsed_ms": 20,
        "errors": [],
    }
    data.update(overrides)
    return [[json.dumps(data)]]


def test_failed_collector_is_critical() -> None:
    """Failed/incomplete collection must remain operationally visible."""

    section = parse_s2d_hci_collector_health(_health(success=False, complete=False, errors=["boom"]))
    result = list(check_s2d_hci_collector_health("fast", section))[0]
    assert result.state == State.CRIT
    assert "boom" in result.summary


def test_disabled_virtualization_is_explicit_ok() -> None:
    """An intentionally disabled collector must be distinguishable from data loss."""

    section = parse_s2d_hci_collector_health(_health(collector="virtualization", role="disabled"))
    result = list(check_s2d_hci_collector_health("virtualization", section))[0]
    assert result.state == State.OK
    assert "disabled" in result.summary.lower()


def test_bad_health_json_is_unknown() -> None:
    """Malformed health telemetry must itself produce an UNKNOWN service."""

    section = parse_s2d_hci_collector_health([["not-json"]])
    item = next(iter(section))
    result = list(check_s2d_hci_collector_health(item, section))[0]
    assert result.state == State.UNKNOWN
