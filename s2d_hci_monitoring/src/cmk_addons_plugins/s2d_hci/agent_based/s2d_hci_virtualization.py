#!/usr/bin/env python3
"""Monitor Hyper-V host and workload state on Windows HCI cluster nodes.

The module consumes JSON-lines sections from the read-only virtualization
collector and registers services for the host, workloads, integration
services, replication, checkpoints, virtual NICs, and attached virtual disks.
Optional or unsupported data is surfaced conservatively as UNKNOWN.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Result, Service, State, check_levels


@dataclass(frozen=True)
class WorkloadObject:
    """Normalized workload object and original collector details."""

    name: str
    state: str
    details: Mapping[str, object]


Section = Mapping[str, WorkloadObject]


def _parse_json_objects(string_table: Sequence[Sequence[str]], name_fields: Sequence[str]) -> Section:
    """Parse valid JSON rows and index them by the first available name field."""

    parsed: dict[str, WorkloadObject] = {}
    for row in string_table:
        if not row:
            continue
        try:
            data = json.loads(" ".join(row))
        except json.JSONDecodeError:
            continue
        name = ""
        for field in name_fields:
            if data.get(field):
                name = str(data[field])
                break
        if not name:
            continue
        state = str(data.get("state") or data.get("status") or data.get("health") or data.get("primary_status_description") or "unknown")
        parsed[name] = WorkloadObject(name=name, state=state, details=data)
    return parsed


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "enabled"}:
        return True
    if normalized in {"false", "0", "no", "disabled"}:
        return False
    return None


def _state_from_text(value: object) -> State:
    normalized = str(value or "").strip().lower()
    if normalized in {"ok", "online", "running", "operating normally", "normal", "healthy", "true"}:
        return State.OK
    if normalized in {"paused", "saved", "warning", "degraded", "resynchronizing", "suspended"}:
        return State.WARN
    if normalized in {"off", "offline", "critical", "failed", "error", "notfound", "false"}:
        return State.CRIT
    return State.UNKNOWN


def _discover_items(section: Section):
    for item in section:
        yield Service(item=item)


def parse_s2d_hci_virtualization_host(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_json_objects(string_table, ["name"])


agent_section_s2d_hci_virtualization_host = AgentSection(
    name="s2d_hci_virtualization_host",
    parse_function=parse_s2d_hci_virtualization_host,
)


def discover_s2d_hci_virtualization_host(section: Section):
    yield from _discover_items(section)


def check_s2d_hci_virtualization_host(item: str, section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Virtualization host {item!r} not found")
        return
    entry = section[item]
    service_status = str(entry.details.get("service_status") or "unknown")
    module_available_value = entry.details.get("module_available")
    module_available = "unknown" if module_available_value is None else str(module_available_value)
    state = _state_from_text(service_status)
    if module_available_value is False or module_available.lower() == "false":
        state = State.CRIT
    yield Result(state=state, summary=f"Service: {service_status}, module: {module_available}", details=str(entry.details))


check_plugin_s2d_hci_virtualization_host = CheckPlugin(
    name="s2d_hci_virtualization_host",
    service_name="S2D/HCI virtualization host %s",
    discovery_function=discover_s2d_hci_virtualization_host,
    check_function=check_s2d_hci_virtualization_host,
)


def parse_s2d_hci_virtualization_workloads(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_json_objects(string_table, ["name"])


agent_section_s2d_hci_virtualization_workloads = AgentSection(
    name="s2d_hci_virtualization_workloads",
    parse_function=parse_s2d_hci_virtualization_workloads,
)


def discover_s2d_hci_virtualization_workloads(section: Section):
    yield from _discover_items(section)


def check_s2d_hci_virtualization_workloads(item: str, params: Mapping[str, object], section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Virtualization workload {item!r} not found")
        return
    entry = section[item]
    cpu_usage = _as_float(entry.details.get("cpu_usage"))
    if cpu_usage is not None:
        yield from check_levels(
            cpu_usage,
            levels_upper=params.get("levels_upper_cpu", ("fixed", (80.0, 95.0))),
            metric_name="s2d_hci_virtualization_workload_cpu_usage",
            label="CPU usage",
            boundaries=(0.0, 100.0),
        )
    memory_demand = _as_float(entry.details.get("memory_demand"))
    memory_assigned = _as_float(entry.details.get("memory_assigned"))
    if memory_demand is not None and memory_assigned and memory_assigned > 0:
        pressure = (memory_demand / memory_assigned) * 100.0
        yield from check_levels(
            pressure,
            levels_upper=params.get("levels_upper_memory_pressure", ("fixed", (100.0, 120.0))),
            metric_name="s2d_hci_virtualization_workload_memory_pressure",
            label="Memory pressure",
        )
    yield Result(state=_state_from_text(entry.state), summary=f"State: {entry.state}", details=str(entry.details))


check_plugin_s2d_hci_virtualization_workloads = CheckPlugin(
    name="s2d_hci_virtualization_workloads",
    service_name="S2D/HCI virtualization workload %s",
    discovery_function=discover_s2d_hci_virtualization_workloads,
    check_function=check_s2d_hci_virtualization_workloads,
    check_default_parameters={"levels_upper_cpu": ("fixed", (80.0, 95.0)), "levels_upper_memory_pressure": ("fixed", (100.0, 120.0))},
    check_ruleset_name="s2d_hci_virtualization_workloads",
)


def parse_s2d_hci_virtualization_services(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_json_objects(string_table, ["name"])


agent_section_s2d_hci_virtualization_services = AgentSection(
    name="s2d_hci_virtualization_services",
    parse_function=parse_s2d_hci_virtualization_services,
)


def discover_s2d_hci_virtualization_services(section: Section):
    yield from _discover_items(section)


def check_s2d_hci_virtualization_services(item: str, section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Virtualization integration service {item!r} not found")
        return
    entry = section[item]
    enabled = _as_bool(entry.details.get("enabled"))
    primary = str(entry.details.get("primary_status_description") or "unknown")
    state = State.OK
    if enabled is True and primary.lower() not in {"ok", "operating normally"}:
        state = State.WARN
    yield Result(state=state, summary=f"Enabled: {enabled}, primary status: {primary}", details=str(entry.details))


check_plugin_s2d_hci_virtualization_services = CheckPlugin(
    name="s2d_hci_virtualization_services",
    service_name="S2D/HCI virtualization integration %s",
    discovery_function=discover_s2d_hci_virtualization_services,
    check_function=check_s2d_hci_virtualization_services,
)


def parse_s2d_hci_virtualization_replication(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_json_objects(string_table, ["name"])


agent_section_s2d_hci_virtualization_replication = AgentSection(
    name="s2d_hci_virtualization_replication",
    parse_function=parse_s2d_hci_virtualization_replication,
)


def discover_s2d_hci_virtualization_replication(section: Section):
    yield from _discover_items(section)


def check_s2d_hci_virtualization_replication(item: str, section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Virtualization replication {item!r} not found")
        return
    entry = section[item]
    if entry.details.get("available") is False:
        yield Result(state=State.UNKNOWN, summary=str(entry.details.get("reason") or "Replication data unavailable"), details=str(entry.details))
        return
    health = str(entry.details.get("health") or "unknown")
    yield Result(state=_state_from_text(health), summary=f"Replication health: {health}, state: {entry.details.get('state', 'n/a')}", details=str(entry.details))


check_plugin_s2d_hci_virtualization_replication = CheckPlugin(
    name="s2d_hci_virtualization_replication",
    service_name="S2D/HCI virtualization replication %s",
    discovery_function=discover_s2d_hci_virtualization_replication,
    check_function=check_s2d_hci_virtualization_replication,
)


def parse_s2d_hci_virtualization_checkpoints(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_json_objects(string_table, ["name"])


agent_section_s2d_hci_virtualization_checkpoints = AgentSection(
    name="s2d_hci_virtualization_checkpoints",
    parse_function=parse_s2d_hci_virtualization_checkpoints,
)


def discover_s2d_hci_virtualization_checkpoints(section: Section):
    yield from _discover_items(section)


def _checkpoint_age_hours(value: object) -> float | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        created = datetime.fromisoformat(text)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - created.astimezone(timezone.utc)).total_seconds() / 3600.0
    except ValueError:
        return None


def check_s2d_hci_virtualization_checkpoints(item: str, params: Mapping[str, object], section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Virtualization checkpoint {item!r} not found")
        return
    entry = section[item]
    age_hours = _checkpoint_age_hours(entry.details.get("creation_time"))
    if age_hours is None:
        yield Result(state=State.WARN, summary="Checkpoint exists, age unknown", details=str(entry.details))
        return
    yield from check_levels(
        age_hours,
        levels_upper=params.get("levels_upper_age_hours", ("fixed", (24.0, 72.0))),
        metric_name="s2d_hci_virtualization_checkpoint_age_hours",
        label="Checkpoint age",
    )
    yield Result(state=State.OK, summary=f"Checkpoint exists, age: {age_hours:.1f} h", details=str(entry.details))


check_plugin_s2d_hci_virtualization_checkpoints = CheckPlugin(
    name="s2d_hci_virtualization_checkpoints",
    service_name="S2D/HCI virtualization checkpoint %s",
    discovery_function=discover_s2d_hci_virtualization_checkpoints,
    check_function=check_s2d_hci_virtualization_checkpoints,
    check_default_parameters={"levels_upper_age_hours": ("fixed", (24.0, 72.0))},
    check_ruleset_name="s2d_hci_virtualization_checkpoints",
)


def parse_s2d_hci_virtualization_network_adapters(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_json_objects(string_table, ["name"])


agent_section_s2d_hci_virtualization_network_adapters = AgentSection(
    name="s2d_hci_virtualization_network_adapters",
    parse_function=parse_s2d_hci_virtualization_network_adapters,
)


def discover_s2d_hci_virtualization_network_adapters(section: Section):
    yield from _discover_items(section)


def check_s2d_hci_virtualization_network_adapters(item: str, section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Virtualization network adapter {item!r} not found")
        return
    entry = section[item]
    connected = _as_bool(entry.details.get("connected"))
    switch_name = entry.details.get("switch_name")
    state = State.OK
    if connected is False or not switch_name:
        state = State.CRIT
    yield Result(state=state, summary=f"Connected: {connected}, switch: {switch_name or 'n/a'}", details=str(entry.details))


check_plugin_s2d_hci_virtualization_network_adapters = CheckPlugin(
    name="s2d_hci_virtualization_network_adapters",
    service_name="S2D/HCI virtualization network adapter %s",
    discovery_function=discover_s2d_hci_virtualization_network_adapters,
    check_function=check_s2d_hci_virtualization_network_adapters,
)


def parse_s2d_hci_virtualization_hard_disks(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_json_objects(string_table, ["name", "path"])


agent_section_s2d_hci_virtualization_hard_disks = AgentSection(
    name="s2d_hci_virtualization_hard_disks",
    parse_function=parse_s2d_hci_virtualization_hard_disks,
)


def discover_s2d_hci_virtualization_hard_disks(section: Section):
    yield from _discover_items(section)


def check_s2d_hci_virtualization_hard_disks(item: str, section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Virtualization hard disk {item!r} not found")
        return
    entry = section[item]
    parent_path = entry.details.get("parent_path")
    vhd_type = entry.details.get("vhd_type")
    state = State.OK
    summary = f"Disk type: {vhd_type or 'unknown'}, path: {entry.details.get('path', 'n/a')}"
    if parent_path:
        state = State.WARN
        summary = f"Differencing disk parent: {parent_path}"
    yield Result(state=state, summary=summary, details=str(entry.details))


check_plugin_s2d_hci_virtualization_hard_disks = CheckPlugin(
    name="s2d_hci_virtualization_hard_disks",
    service_name="S2D/HCI virtualization disk %s",
    discovery_function=discover_s2d_hci_virtualization_hard_disks,
    check_function=check_s2d_hci_virtualization_hard_disks,
)
