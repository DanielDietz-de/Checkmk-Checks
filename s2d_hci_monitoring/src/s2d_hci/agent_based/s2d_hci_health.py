#!/usr/bin/env python3
"""Evaluate Storage Spaces Direct and storage-health report output.

The module parses JSON-lines sections emitted by the Windows health collector
and registers Check API V2 services. Unsupported optional Windows cmdlets are
reported as UNKNOWN instead of being misclassified as an unhealthy cluster.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Result, Service, State


@dataclass(frozen=True)
class HealthObject:
    """Normalized health object and its original collector details."""

    name: str
    state: str
    details: Mapping[str, object]


Section = Mapping[str, HealthObject]


def _get_field(data: Mapping[str, object], *names: str) -> object | None:
    """Return a field using case- and underscore-insensitive matching."""

    normalized = {str(key).replace("_", "").lower(): value for key, value in data.items()}
    for name in names:
        key = name.replace("_", "").lower()
        if key in normalized:
            return normalized[key]
    return None


def _parse_health_objects(string_table: Sequence[Sequence[str]], name_fields: Sequence[str]) -> Section:
    """Parse valid JSON rows and retain stable names for service discovery."""

    parsed: dict[str, HealthObject] = {}
    for index, row in enumerate(string_table, start=1):
        if not row:
            continue
        try:
            data = json.loads(" ".join(row))
        except json.JSONDecodeError:
            continue
        name = ""
        for field in name_fields:
            value = _get_field(data, field)
            if value:
                name = str(value)
                break
        if not name:
            name = str(_get_field(data, "section") or f"entry_{index}")
        state = str(
            _get_field(data, "health_status")
            or _get_field(data, "operational_status")
            or _get_field(data, "state")
            or _get_field(data, "severity")
            or _get_field(data, "success")
            or _get_field(data, "available")
            or "unknown"
        )
        parsed[name] = HealthObject(name=name, state=state, details=data)
    return parsed


def _state_from_health(value: str) -> State:
    """Map health text to a conservative Checkmk state."""

    normalized = value.lower()
    if any(token in normalized for token in ["unhealthy", "critical", "failed", "error", "offline", "false", "disabled"]):
        return State.CRIT
    if any(token in normalized for token in ["warning", "degraded", "incomplete", "stressed"]):
        return State.WARN
    if any(token in normalized for token in ["healthy", "ok", "online", "true", "enabled"]):
        return State.OK
    return State.UNKNOWN


def parse_s2d_hci_s2d_state(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_health_objects(string_table, ["name", "friendly_name"])


agent_section_s2d_hci_s2d_state = AgentSection(name="s2d_hci_s2d_state", parse_function=parse_s2d_hci_s2d_state)


def discover_s2d_hci_s2d_state(section: Section):
    if section:
        yield Service()


def check_s2d_hci_s2d_state(section: Section):
    if not section:
        yield Result(state=State.UNKNOWN, summary="No S2D state data found")
        return
    entry = next(iter(section.values()))
    if _get_field(entry.details, "available") is False:
        yield Result(state=State.UNKNOWN, summary=str(_get_field(entry.details, "reason") or "S2D state command is unavailable"), details=str(entry.details))
        return
    yield Result(state=_state_from_health(entry.state), summary=f"S2D state: {entry.state}", details=str(entry.details))


check_plugin_s2d_hci_s2d_state = CheckPlugin(
    name="s2d_hci_s2d_state",
    service_name="S2D/HCI S2D state",
    discovery_function=discover_s2d_hci_s2d_state,
    check_function=check_s2d_hci_s2d_state,
)


def parse_s2d_hci_storage_subsystems(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_health_objects(string_table, ["friendly_name", "name"])


agent_section_s2d_hci_storage_subsystems = AgentSection(
    name="s2d_hci_storage_subsystems",
    parse_function=parse_s2d_hci_storage_subsystems,
)


def discover_s2d_hci_storage_subsystems(section: Section):
    for item in section:
        yield Service(item=item)


def check_s2d_hci_storage_subsystems(item: str, section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Storage subsystem {item!r} not found")
        return
    entry = section[item]
    operational = str(_get_field(entry.details, "operational_status") or "unknown")
    yield Result(
        state=_state_from_health(f"{entry.state} {operational}"),
        summary=f"Health: {entry.state}, operational: {operational}",
        details=str(entry.details),
    )


check_plugin_s2d_hci_storage_subsystems = CheckPlugin(
    name="s2d_hci_storage_subsystems",
    service_name="S2D/HCI storage subsystem %s",
    discovery_function=discover_s2d_hci_storage_subsystems,
    check_function=check_s2d_hci_storage_subsystems,
)


def parse_s2d_hci_storage_health_report(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_health_objects(string_table, ["subsystem", "name", "fault_domain", "title"])


agent_section_s2d_hci_storage_health_report = AgentSection(
    name="s2d_hci_storage_health_report",
    parse_function=parse_s2d_hci_storage_health_report,
)


def discover_s2d_hci_storage_health_report(section: Section):
    for item in section:
        yield Service(item=item)


def check_s2d_hci_storage_health_report(item: str, section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Storage health report item {item!r} not found")
        return
    entry = section[item]
    if _get_field(entry.details, "available") is False:
        yield Result(state=State.UNKNOWN, summary=str(_get_field(entry.details, "reason") or "Storage health report command is unavailable"), details=str(entry.details))
        return
    yield Result(state=_state_from_health(entry.state), summary=f"Health report state: {entry.state}", details=str(entry.details))


check_plugin_s2d_hci_storage_health_report = CheckPlugin(
    name="s2d_hci_storage_health_report",
    service_name="S2D/HCI storage health report %s",
    discovery_function=discover_s2d_hci_storage_health_report,
    check_function=check_s2d_hci_storage_health_report,
)
