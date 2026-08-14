"""Protocol parser tests for malformed, duplicate, mixed-run, and bounded numeric input."""

from __future__ import annotations

import json

from cmk.agent_based.v2 import State
from s2d_hci.agent_based.s2d_hci_protocol import as_float, parse_protocol_objects, state_from_text


def _line(**values: object) -> list[str]:
    """Return one agent string-table row containing compact JSON."""

    return [json.dumps(values, separators=(",", ":"))]


def test_malformed_json_becomes_visible_parser_error() -> None:
    """Malformed input must not vanish from service discovery."""

    section = parse_protocol_objects([["{broken"]])
    assert len(section) == 1
    entry = next(iter(section.values()))
    assert entry.issue and "Malformed JSON" in entry.issue


def test_duplicate_identity_is_preserved_as_error() -> None:
    """A duplicate object must retain the first object and add a visible error."""

    section = parse_protocol_objects(
        [
            _line(protocol_version=1, run_id="a", identity="same", name="one", state="up"),
            _line(protocol_version=1, run_id="a", identity="same", name="two", state="up"),
        ]
    )
    assert "same" in section
    assert len(section) == 2
    assert any(entry.issue and "Duplicate stable identity" in entry.issue for entry in section.values())


def test_mixed_run_ids_become_visible_protocol_error() -> None:
    """Rows from different collector invocations must never be combined into one logical snapshot."""

    section = parse_protocol_objects(
        [
            _line(protocol_version=1, run_id="run-a", identity="first", name="one", state="up"),
            _line(protocol_version=1, run_id="run-b", identity="second", name="two", state="up"),
        ]
    )
    assert "first" in section
    assert "second" not in section
    assert len(section) == 2
    assert any(entry.issue and "Mixed collector run_id" in entry.issue for entry in section.values())


def test_missing_protocol_is_visible() -> None:
    """Records without the supported protocol version must become parser errors."""

    section = parse_protocol_objects([_line(run_id="a", identity="node", state="up")])
    assert next(iter(section.values())).issue


def test_non_finite_numbers_are_rejected() -> None:
    """NaN and infinity must never be emitted as Checkmk metrics."""

    assert as_float("nan") is None
    assert as_float("inf") is None
    assert as_float(12.5) == 12.5


def test_unknown_state_defaults_unknown() -> None:
    """Unrecognized Microsoft states must not be classified as healthy."""

    assert state_from_text("new-vendor-state") == State.UNKNOWN


def test_unhealthy_state_uses_offline_policy() -> None:
    """Microsoft Unhealthy health status must map through the offline policy instead of degrading to an ambiguous UNKNOWN state."""

    assert state_from_text("Unhealthy") == State.CRIT
