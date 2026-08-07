#!/usr/bin/env python3
"""Monitor opt-in Hyper-V telemetry emitted to stable VM piggyback hosts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Result, State, check_levels

from .s2d_hci_protocol import (
    DEFAULT_STATE_POLICY,
    Section,
    as_bool,
    as_float,
    collector_error,
    discover_items,
    parse_protocol_objects,
    state_from_text,
)

STATE_DEFAULTS = dict(DEFAULT_STATE_POLICY)
WORKLOAD_DEFAULTS: Mapping[str, object] = {
    "levels_upper_cpu": ("fixed", (80.0, 95.0)),
    "levels_upper_memory_pressure": ("fixed", (100.0, 120.0)),
    **STATE_DEFAULTS,
}
CHECKPOINT_DEFAULTS: Mapping[str, object] = {
    "levels_upper_age_hours": ("fixed", (24.0, 72.0)),
}


def _parse_virtualization(
    string_table: Sequence[Sequence[str]],
    *,
    identity_fields: Sequence[str] = ("identity", "vm_id", "name", "section"),
    display_fields: Sequence[str] = ("name", "section"),
    fallback_name: str,
) -> Section:
    """Parse one VM-scoped section using protocol and duplicate validation."""

    return parse_protocol_objects(
        string_table,
        identity_fields=identity_fields,
        display_fields=display_fields,
        state_fields=("state", "status", "health", "primary_status_description", "success", "available"),
        fallback_name=fallback_name,
    )


def _entry_or_unknown(item: str, section: Section, label: str):
    """Return an entry or an UNKNOWN result for missing/failed collector data."""

    entry = section.get(item)
    if entry is None:
        return None, Result(state=State.UNKNOWN, summary=f"{label} {item!r} not found")
    error = collector_error(entry)
    if error:
        return None, Result(state=State.UNKNOWN, summary=f"{label} collection failed: {error}", details=str(entry.details))
    return entry, None


def parse_s2d_hci_virtualization_host(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse local Hyper-V host state."""

    return _parse_virtualization(string_table, identity_fields=("identity", "name", "section"), fallback_name="Hyper-V host")


agent_section_s2d_hci_virtualization_host = AgentSection(
    name="s2d_hci_virtualization_host",
    parse_function=parse_s2d_hci_virtualization_host,
)


def discover_s2d_hci_virtualization_host(section: Section):
    """Discover Hyper-V host and synthetic error services."""

    yield from discover_items(section)


def check_s2d_hci_virtualization_host(item: str, params: Mapping[str, object], section: Section):
    """Evaluate the Hyper-V management service and module availability."""

    entry, error_result = _entry_or_unknown(item, section, "Virtualization host")
    if error_result:
        yield error_result
        return
    assert entry is not None
    module_available = as_bool(entry.details.get("module_available"))
    if module_available is False:
        yield Result(state=State.CRIT, summary="Hyper-V module is unavailable", details=str(entry.details))
        return
    service_status = str(entry.details.get("service_status") or entry.state)
    yield Result(state=state_from_text(service_status, params), summary=f"VMMS service: {service_status}", details=str(entry.details))


check_plugin_s2d_hci_virtualization_host = CheckPlugin(
    name="s2d_hci_virtualization_host",
    service_name="S2D/HCI virtualization host %s",
    discovery_function=discover_s2d_hci_virtualization_host,
    check_function=check_s2d_hci_virtualization_host,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)


def parse_s2d_hci_virtualization_workloads(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse one VM workload record on its stable VM-GUID piggyback host."""

    return _parse_virtualization(string_table, identity_fields=("vm_id", "identity", "name", "section"), fallback_name="VM workload")


agent_section_s2d_hci_virtualization_workloads = AgentSection(
    name="s2d_hci_virtualization_workloads",
    parse_function=parse_s2d_hci_virtualization_workloads,
)


def discover_s2d_hci_virtualization_workloads(section: Section):
    """Discover VM workload services."""

    yield from discover_items(section)


def check_s2d_hci_virtualization_workloads(item: str, params: Mapping[str, object], section: Section):
    """Evaluate VM state, CPU usage, and memory pressure using configurable thresholds."""

    entry, error_result = _entry_or_unknown(item, section, "Virtualization workload")
    if error_result:
        yield error_result
        return
    assert entry is not None
    cpu = as_float(entry.details.get("cpu_usage"))
    if cpu is not None:
        yield from check_levels(
            cpu,
            levels_upper=params.get("levels_upper_cpu", ("fixed", (80.0, 95.0))),
            metric_name="s2d_hci_virtualization_workload_cpu_usage",
            label="CPU usage",
            boundaries=(0.0, 100.0),
        )
    demand = as_float(entry.details.get("memory_demand"))
    assigned = as_float(entry.details.get("memory_assigned"))
    if demand is not None and assigned is not None and assigned > 0:
        pressure = demand / assigned * 100.0
        yield from check_levels(
            pressure,
            levels_upper=params.get("levels_upper_memory_pressure", ("fixed", (100.0, 120.0))),
            metric_name="s2d_hci_virtualization_workload_memory_pressure",
            label="Memory pressure",
        )
    yield Result(state=state_from_text(entry.state, params), summary=f"VM: {entry.name}, state: {entry.state}", details=str(entry.details))


check_plugin_s2d_hci_virtualization_workloads = CheckPlugin(
    name="s2d_hci_virtualization_workloads",
    service_name="S2D/HCI virtualization workload %s",
    discovery_function=discover_s2d_hci_virtualization_workloads,
    check_function=check_s2d_hci_virtualization_workloads,
    check_default_parameters=WORKLOAD_DEFAULTS,
    check_ruleset_name="s2d_hci_virtualization_workloads",
)


def parse_s2d_hci_virtualization_services(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse Hyper-V integration services using per-VM stable names."""

    return _parse_virtualization(string_table, identity_fields=("identity", "name", "section"), fallback_name="Integration service")


agent_section_s2d_hci_virtualization_services = AgentSection(
    name="s2d_hci_virtualization_services",
    parse_function=parse_s2d_hci_virtualization_services,
)


def discover_s2d_hci_virtualization_services(section: Section):
    """Discover Hyper-V integration-service checks."""

    yield from discover_items(section)


def check_s2d_hci_virtualization_services(item: str, params: Mapping[str, object], section: Section):
    """Warn when an enabled integration service is not operating normally."""

    entry, error_result = _entry_or_unknown(item, section, "Integration service")
    if error_result:
        yield error_result
        return
    assert entry is not None
    enabled = as_bool(entry.details.get("enabled"))
    primary = str(entry.details.get("primary_status_description") or entry.state)
    if enabled is False:
        state = State.OK
    elif enabled is True and primary.strip().lower() in {"ok", "operating normally"}:
        state = State.OK
    else:
        state = state_from_text(primary, params)
    yield Result(state=state, summary=f"Integration service: {entry.name}, enabled: {enabled}, status: {primary}", details=str(entry.details))


check_plugin_s2d_hci_virtualization_services = CheckPlugin(
    name="s2d_hci_virtualization_services",
    service_name="S2D/HCI virtualization integration %s",
    discovery_function=discover_s2d_hci_virtualization_services,
    check_function=check_s2d_hci_virtualization_services,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)


def parse_s2d_hci_virtualization_replication(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse optional VM replication state."""

    return _parse_virtualization(string_table, identity_fields=("identity", "name", "section"), fallback_name="VM replication")


agent_section_s2d_hci_virtualization_replication = AgentSection(
    name="s2d_hci_virtualization_replication",
    parse_function=parse_s2d_hci_virtualization_replication,
)


def discover_s2d_hci_virtualization_replication(section: Section):
    """Discover VM replication checks."""

    yield from discover_items(section)


def check_s2d_hci_virtualization_replication(item: str, params: Mapping[str, object], section: Section):
    """Evaluate replication health or report unsupported replication telemetry as UNKNOWN."""

    entry, error_result = _entry_or_unknown(item, section, "Replication")
    if error_result:
        yield error_result
        return
    assert entry is not None
    if entry.details.get("available") is False:
        yield Result(state=State.UNKNOWN, summary=str(entry.details.get("reason") or "Replication data unavailable"), details=str(entry.details))
        return
    health = str(entry.details.get("health") or entry.state)
    yield Result(state=state_from_text(health, params), summary=f"Replication health: {health}", details=str(entry.details))


check_plugin_s2d_hci_virtualization_replication = CheckPlugin(
    name="s2d_hci_virtualization_replication",
    service_name="S2D/HCI virtualization replication %s",
    discovery_function=discover_s2d_hci_virtualization_replication,
    check_function=check_s2d_hci_virtualization_replication,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)


def parse_s2d_hci_virtualization_checkpoints(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse VM checkpoints using stable checkpoint identifiers."""

    return _parse_virtualization(string_table, identity_fields=("identity", "name", "section"), fallback_name="VM checkpoint")


agent_section_s2d_hci_virtualization_checkpoints = AgentSection(
    name="s2d_hci_virtualization_checkpoints",
    parse_function=parse_s2d_hci_virtualization_checkpoints,
)


def discover_s2d_hci_virtualization_checkpoints(section: Section):
    """Discover retained VM checkpoint services."""

    yield from discover_items(section)


def _checkpoint_age_hours(value: object) -> float | None:
    """Return UTC checkpoint age in hours or ``None`` for malformed timestamps."""

    if not value:
        return None
    try:
        created = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - created.astimezone(timezone.utc)).total_seconds() / 3600.0


def check_s2d_hci_virtualization_checkpoints(item: str, params: Mapping[str, object], section: Section):
    """Evaluate checkpoint age and report malformed timestamps conservatively."""

    entry, error_result = _entry_or_unknown(item, section, "Checkpoint")
    if error_result:
        yield error_result
        return
    assert entry is not None
    age = _checkpoint_age_hours(entry.details.get("creation_time"))
    if age is None:
        yield Result(state=State.UNKNOWN, summary=f"Checkpoint {entry.name} exists but age is unavailable", details=str(entry.details))
        return
    yield from check_levels(
        age,
        levels_upper=params.get("levels_upper_age_hours", ("fixed", (24.0, 72.0))),
        metric_name="s2d_hci_virtualization_checkpoint_age_hours",
        label="Checkpoint age",
    )


check_plugin_s2d_hci_virtualization_checkpoints = CheckPlugin(
    name="s2d_hci_virtualization_checkpoints",
    service_name="S2D/HCI virtualization checkpoint %s",
    discovery_function=discover_s2d_hci_virtualization_checkpoints,
    check_function=check_s2d_hci_virtualization_checkpoints,
    check_default_parameters=CHECKPOINT_DEFAULTS,
    check_ruleset_name="s2d_hci_virtualization_checkpoints",
)


def parse_s2d_hci_virtualization_network_adapters(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse VM virtual NICs using stable adapter identities."""

    return _parse_virtualization(string_table, identity_fields=("identity", "name", "section"), fallback_name="VM network adapter")


agent_section_s2d_hci_virtualization_network_adapters = AgentSection(
    name="s2d_hci_virtualization_network_adapters",
    parse_function=parse_s2d_hci_virtualization_network_adapters,
)


def discover_s2d_hci_virtualization_network_adapters(section: Section):
    """Discover VM virtual-NIC services."""

    yield from discover_items(section)


def check_s2d_hci_virtualization_network_adapters(item: str, params: Mapping[str, object], section: Section):
    """Evaluate virtual-NIC connectivity and switch attachment."""

    entry, error_result = _entry_or_unknown(item, section, "Network adapter")
    if error_result:
        yield error_result
        return
    assert entry is not None
    connected = as_bool(entry.details.get("connected"))
    switch = str(entry.details.get("switch_name") or "")
    if connected is False or not switch:
        state = state_from_text("offline", params)
    elif connected is True:
        state = State.OK
    else:
        state = state_from_text("unknown", params)
    yield Result(state=state, summary=f"Adapter: {entry.name}, connected: {connected}, switch: {switch or 'n/a'}", details=str(entry.details))


check_plugin_s2d_hci_virtualization_network_adapters = CheckPlugin(
    name="s2d_hci_virtualization_network_adapters",
    service_name="S2D/HCI virtualization network adapter %s",
    discovery_function=discover_s2d_hci_virtualization_network_adapters,
    check_function=check_s2d_hci_virtualization_network_adapters,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)


def parse_s2d_hci_virtualization_hard_disks(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse VM hard disks using controller-based stable identities."""

    return _parse_virtualization(string_table, identity_fields=("identity", "name", "section"), fallback_name="VM hard disk")


agent_section_s2d_hci_virtualization_hard_disks = AgentSection(
    name="s2d_hci_virtualization_hard_disks",
    parse_function=parse_s2d_hci_virtualization_hard_disks,
)


def discover_s2d_hci_virtualization_hard_disks(section: Section):
    """Discover VM hard-disk services."""

    yield from discover_items(section)


def check_s2d_hci_virtualization_hard_disks(item: str, params: Mapping[str, object], section: Section):
    """Warn on inaccessible VHD metadata or differencing-disk parents."""

    entry, error_result = _entry_or_unknown(item, section, "Virtual disk")
    if error_result:
        yield error_result
        return
    assert entry is not None
    if entry.details.get("vhd_error"):
        yield Result(state=State.WARN, summary=f"VHD metadata unavailable: {entry.details.get('vhd_error')}", details=str(entry.details))
        return
    if entry.details.get("parent_path"):
        yield Result(state=State.WARN, summary="Differencing disk has a parent VHD", details=str(entry.details))
        return
    yield Result(state=State.OK, summary=f"Disk: {entry.name}, type: {entry.details.get('vhd_type', 'n/a')}", details=str(entry.details))


check_plugin_s2d_hci_virtualization_hard_disks = CheckPlugin(
    name="s2d_hci_virtualization_hard_disks",
    service_name="S2D/HCI virtualization disk %s",
    discovery_function=discover_s2d_hci_virtualization_hard_disks,
    check_function=check_s2d_hci_virtualization_hard_disks,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)
