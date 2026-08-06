#!/usr/bin/env python3
"""Report availability and record count for optional HCI performance history.

The Windows collector may emit an explicit unsupported-command record. That
condition is UNKNOWN because the optional telemetry is unavailable, not proof
that cluster performance is unhealthy.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Result, Service, State


@dataclass(frozen=True)
class PerfRecord:
    """One collector performance-history record."""

    details: Mapping[str, object]


Section = Sequence[PerfRecord]


def parse_s2d_hci_performance_history(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse valid JSON performance-history rows."""

    parsed: list[PerfRecord] = []
    for row in string_table:
        if not row:
            continue
        try:
            data = json.loads(" ".join(row))
        except json.JSONDecodeError:
            continue
        parsed.append(PerfRecord(details=data))
    return parsed


agent_section_s2d_hci_performance_history = AgentSection(
    name="s2d_hci_performance_history",
    parse_function=parse_s2d_hci_performance_history,
)


def discover_s2d_hci_performance_history(section: Section):
    if section:
        yield Service()


def check_s2d_hci_performance_history(section: Section):
    if not section:
        yield Result(state=State.UNKNOWN, summary="No performance history data found")
        return
    unavailable = [record for record in section if record.details.get("available") is False]
    if unavailable:
        reason = unavailable[0].details.get("reason") or "Performance history command is unavailable"
        yield Result(state=State.UNKNOWN, summary=str(reason), details=str(unavailable[0].details))
        return
    yield Result(state=State.OK, summary=f"Performance history records: {len(section)}")


check_plugin_s2d_hci_performance_history = CheckPlugin(
    name="s2d_hci_performance_history",
    service_name="S2D/HCI performance history",
    discovery_function=discover_s2d_hci_performance_history,
    check_function=check_s2d_hci_performance_history,
)
