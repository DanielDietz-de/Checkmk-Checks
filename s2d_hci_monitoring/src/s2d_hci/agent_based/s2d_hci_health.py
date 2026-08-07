#!/usr/bin/env python3
"""Monitor Storage Spaces Direct and storage-health report output."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Result, State

from .s2d_hci_protocol import DEFAULT_STATE_POLICY, Section, collector_error, discover_items, parse_protocol_objects, state_from_text

STATE_DEFAULTS = dict(DEFAULT_STATE_POLICY)


def _parse_health(
    string_table: Sequence[Sequence[str]],
    *,
    display_fields: Sequence[str],
    fallback_name: str,
) -> Section:
    """Parse one health section using the package protocol validator."""

    return parse_protocol_objects(
        string_table,
        identity_fields=("identity", "name", "friendly_name", "subsystem", "section"),
        display_fields=display_fields,
        state_fields=("health_status", "state", "operational_status", "severity", "success", "available"),
        fallback_name=fallback_name,
    )


def _check_health(item: str, params: Mapping[str, object], section: Section, label: str):
    """Evaluate a health object and preserve unsupported-command semantics."""

    entry = section.get(item)
    if entry is None:
        yield Result(state=State.UNKNOWN, summary=f"{label} {item!r} not found")
        return
    error = collector_error(entry)
    if error:
        yield Result(state=State.UNKNOWN, summary=f"{label} collection failed: {error}", details=str(entry.details))
        return
    if entry.details.get("available") is False:
        yield Result(
            state=State.UNKNOWN,
            summary=str(entry.details.get("reason") or f"{label} command is unavailable"),
            details=str(entry.details),
        )
        return
    operational = str(entry.details.get("operational_status") or "")
    combined = f"{entry.state} {operational}".strip()
    yield Result(
        state=state_from_text(combined, params),
        summary=f"{label}: {entry.name}, state: {entry.state}, operational: {operational or 'n/a'}",
        details=str(entry.details),
    )


def parse_s2d_hci_s2d_state(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse normalized S2D state output independent of native property casing."""

    return _parse_health(string_table, display_fields=("name",), fallback_name="Storage Spaces Direct")


agent_section_s2d_hci_s2d_state = AgentSection(name="s2d_hci_s2d_state", parse_function=parse_s2d_hci_s2d_state)


def discover_s2d_hci_s2d_state(section: Section):
    """Discover S2D state and synthetic error services."""

    yield from discover_items(section)


def check_s2d_hci_s2d_state(item: str, params: Mapping[str, object], section: Section):
    """Evaluate normalized S2D state with configurable operational policy."""

    yield from _check_health(item, params, section, "S2D state")


check_plugin_s2d_hci_s2d_state = CheckPlugin(
    name="s2d_hci_s2d_state",
    service_name="S2D/HCI S2D state %s",
    discovery_function=discover_s2d_hci_s2d_state,
    check_function=check_s2d_hci_s2d_state,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)


def parse_s2d_hci_storage_subsystems(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse storage subsystem health using stable collector identities."""

    return _parse_health(string_table, display_fields=("friendly_name", "name"), fallback_name="Storage subsystem")


agent_section_s2d_hci_storage_subsystems = AgentSection(
    name="s2d_hci_storage_subsystems",
    parse_function=parse_s2d_hci_storage_subsystems,
)


def discover_s2d_hci_storage_subsystems(section: Section):
    """Discover storage subsystem services."""

    yield from discover_items(section)


def check_s2d_hci_storage_subsystems(item: str, params: Mapping[str, object], section: Section):
    """Evaluate storage subsystem health and operational status."""

    yield from _check_health(item, params, section, "Storage subsystem")


check_plugin_s2d_hci_storage_subsystems = CheckPlugin(
    name="s2d_hci_storage_subsystems",
    service_name="S2D/HCI storage subsystem %s",
    discovery_function=discover_s2d_hci_storage_subsystems,
    check_function=check_s2d_hci_storage_subsystems,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)


def parse_s2d_hci_storage_health_report(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse storage-health report rows with per-object failure isolation."""

    return _parse_health(string_table, display_fields=("subsystem", "name"), fallback_name="Storage health report")


agent_section_s2d_hci_storage_health_report = AgentSection(
    name="s2d_hci_storage_health_report",
    parse_function=parse_s2d_hci_storage_health_report,
)


def discover_s2d_hci_storage_health_report(section: Section):
    """Discover storage-health report services."""

    yield from discover_items(section)


def check_s2d_hci_storage_health_report(item: str, params: Mapping[str, object], section: Section):
    """Evaluate storage-health report entries while surfacing unsupported commands."""

    yield from _check_health(item, params, section, "Storage health report")


check_plugin_s2d_hci_storage_health_report = CheckPlugin(
    name="s2d_hci_storage_health_report",
    service_name="S2D/HCI storage health report %s",
    discovery_function=discover_s2d_hci_storage_health_report,
    check_function=check_s2d_hci_storage_health_report,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)
