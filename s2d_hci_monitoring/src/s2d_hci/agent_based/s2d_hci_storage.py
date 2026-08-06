#!/usr/bin/env python3
"""Parse S2D storage inventory and evaluate health and capacity.

The module consumes JSON lines from the Windows storage collector and registers
Check API V2 services for CSVs, pools, virtual disks, volumes, and physical
disks. Invalid rows are skipped; valid rows remain available for monitoring.
"""

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Metric, Result, Service, State, check_levels


@dataclass(frozen=True)
class StorageObject:
    """Normalized storage object and the original collector details."""

    name: str
    health_status: str
    operational_status: str
    percent_free: float | None
    details: Mapping[str, object]


Section = Mapping[str, StorageObject]


def _as_float(value: object) -> float | None:
    """Return a numeric collector value or ``None`` when conversion fails."""

    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_storage_objects(
    string_table: Sequence[Sequence[str]],
    name_fields: Sequence[str],
    name_factory: Callable[[Mapping[str, object]], str] | None = None,
) -> Section:
    """Parse JSON rows and index each object by a stable identifier."""

    parsed: dict[str, StorageObject] = {}
    for row in string_table:
        if not row:
            continue
        try:
            data = json.loads(" ".join(row))
        except json.JSONDecodeError:
            continue
        name = name_factory(data) if name_factory is not None else ""
        if not name:
            for field in name_fields:
                if data.get(field):
                    name = str(data[field])
                    break
        if not name:
            continue
        percent_free = _as_float(data.get("percent_free"))
        parsed[name] = StorageObject(
            name=name,
            health_status=str(data.get("health_status") or data.get("state") or data.get("success") or "unknown"),
            operational_status=str(data.get("operational_status") or "unknown"),
            percent_free=percent_free,
            details=data,
        )
    return parsed


def _health_state(health: str, operational: str) -> State:
    """Map Microsoft health and operational values to a conservative state."""

    combined = f"{health} {operational}".lower()
    if any(token in combined for token in ["unhealthy", "failed", "offline", "detached", "lost", "false"]):
        return State.CRIT
    if any(token in combined for token in ["warning", "degraded", "incomplete", "stressed"]):
        return State.WARN
    if "healthy" in combined or "ok" in combined or "online" in combined or "true" in combined:
        return State.OK
    return State.UNKNOWN


def _discover_items(section: Section):
    for item in section:
        yield Service(item=item)


def parse_s2d_hci_csv(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_storage_objects(string_table, ["name"])


agent_section_s2d_hci_csv = AgentSection(name="s2d_hci_csv", parse_function=parse_s2d_hci_csv)


def discover_s2d_hci_csv(section: Section):
    for item in section:
        yield Service(item=item)


def check_s2d_hci_csv(item: str, params: Mapping[str, object], section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"CSV {item!r} not found")
        return
    entry = section[item]
    state = State.OK if entry.health_status.lower() in {"online", "healthy"} else _health_state(entry.health_status, entry.operational_status)
    if entry.percent_free is not None:
        levels_lower = params.get("levels_lower_free", ("fixed", (15.0, 10.0)))
        yield from check_levels(
            entry.percent_free,
            levels_lower=levels_lower,
            metric_name="s2d_hci_percent_free",
            label="Free space",
            render_func=lambda v: f"{v:.2f}%",
            boundaries=(0.0, 100.0),
        )
        free_summary = f"{entry.percent_free}%"
    else:
        free_summary = "n/a"
    yield Result(state=state, summary=f"State: {entry.health_status}, free: {free_summary}", details=str(entry.details))


check_plugin_s2d_hci_csv = CheckPlugin(
    name="s2d_hci_csv",
    service_name="S2D/HCI CSV %s",
    discovery_function=discover_s2d_hci_csv,
    check_function=check_s2d_hci_csv,
    check_default_parameters={"levels_lower_free": ("fixed", (15.0, 10.0))},
    check_ruleset_name="s2d_hci_csv",
)


def parse_s2d_hci_storage_pools(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_storage_objects(string_table, ["friendly_name"])


agent_section_s2d_hci_storage_pools = AgentSection(name="s2d_hci_storage_pools", parse_function=parse_s2d_hci_storage_pools)


def discover_s2d_hci_storage_pools(section: Section):
    for item in section:
        yield Service(item=item)


def check_s2d_hci_storage_pools(item: str, section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Storage pool {item!r} not found")
        return
    entry = section[item]
    allocated = _as_float(entry.details.get("allocated_size"))
    if allocated is not None:
        yield Metric("s2d_hci_pool_allocated_bytes", allocated)
    yield Result(state=_health_state(entry.health_status, entry.operational_status), summary=f"Health: {entry.health_status}, operational: {entry.operational_status}", details=str(entry.details))


check_plugin_s2d_hci_storage_pools = CheckPlugin(
    name="s2d_hci_storage_pools",
    service_name="S2D/HCI storage pool %s",
    discovery_function=discover_s2d_hci_storage_pools,
    check_function=check_s2d_hci_storage_pools,
)


def parse_s2d_hci_virtual_disks(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_storage_objects(string_table, ["friendly_name"])


agent_section_s2d_hci_virtual_disks = AgentSection(name="s2d_hci_virtual_disks", parse_function=parse_s2d_hci_virtual_disks)


def discover_s2d_hci_virtual_disks(section: Section):
    for item in section:
        yield Service(item=item)


def check_s2d_hci_virtual_disks(item: str, section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Virtual disk {item!r} not found")
        return
    entry = section[item]
    detached_reason = entry.details.get("detached_reason")
    state = _health_state(entry.health_status, entry.operational_status)
    if detached_reason:
        state = State.CRIT
    yield Result(state=state, summary=f"Health: {entry.health_status}, operational: {entry.operational_status}", details=str(entry.details))


check_plugin_s2d_hci_virtual_disks = CheckPlugin(
    name="s2d_hci_virtual_disks",
    service_name="S2D/HCI virtual disk %s",
    discovery_function=discover_s2d_hci_virtual_disks,
    check_function=check_s2d_hci_virtual_disks,
)


def _volume_identifier(data: Mapping[str, object]) -> str:
    """Return a readable identifier that remains unique for duplicate labels."""

    label = str(data.get("filesystem_label") or "").strip()
    drive_letter = str(data.get("drive_letter") or "").strip().rstrip(":")
    path = str(data.get("path") or "").strip()
    locator = f"{drive_letter}:" if drive_letter else path
    if label and locator:
        return f"{label} [{locator}]"
    return locator or label


def parse_s2d_hci_volumes(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_storage_objects(
        string_table,
        ["path", "drive_letter", "filesystem_label"],
        name_factory=_volume_identifier,
    )


agent_section_s2d_hci_volumes = AgentSection(name="s2d_hci_volumes", parse_function=parse_s2d_hci_volumes)


def discover_s2d_hci_volumes(section: Section):
    yield from _discover_items(section)


def check_s2d_hci_volumes(item: str, params: Mapping[str, object], section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Volume {item!r} not found")
        return
    entry = section[item]
    if entry.percent_free is not None:
        levels_lower = params.get("levels_lower_free", ("fixed", (15.0, 10.0)))
        yield from check_levels(
            entry.percent_free,
            levels_lower=levels_lower,
            metric_name="s2d_hci_volume_percent_free",
            label="Free space",
            render_func=lambda v: f"{v:.2f}%",
            boundaries=(0.0, 100.0),
        )
    free_summary = f"{entry.percent_free}%" if entry.percent_free is not None else "n/a"
    yield Result(
        state=_health_state(entry.health_status, entry.operational_status),
        summary=f"Health: {entry.health_status}, operational: {entry.operational_status}, free: {free_summary}",
        details=str(entry.details),
    )


check_plugin_s2d_hci_volumes = CheckPlugin(
    name="s2d_hci_volumes",
    service_name="S2D/HCI volume %s",
    discovery_function=discover_s2d_hci_volumes,
    check_function=check_s2d_hci_volumes,
    check_default_parameters={"levels_lower_free": ("fixed", (15.0, 10.0))},
    check_ruleset_name="s2d_hci_volumes",
)


def parse_s2d_hci_physical_disks(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_storage_objects(string_table, ["serial_number", "friendly_name", "unique_id"])


agent_section_s2d_hci_physical_disks = AgentSection(name="s2d_hci_physical_disks", parse_function=parse_s2d_hci_physical_disks)


def discover_s2d_hci_physical_disks(section: Section):
    for item in section:
        yield Service(item=item)


def check_s2d_hci_physical_disks(item: str, section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Physical disk {item!r} not found")
        return
    entry = section[item]
    summary = f"Health: {entry.health_status}, operational: {entry.operational_status}, usage: {entry.details.get('usage')}"
    yield Result(state=_health_state(entry.health_status, entry.operational_status), summary=summary, details=str(entry.details))


check_plugin_s2d_hci_physical_disks = CheckPlugin(
    name="s2d_hci_physical_disks",
    service_name="S2D/HCI physical disk %s",
    discovery_function=discover_s2d_hci_physical_disks,
    check_function=check_s2d_hci_physical_disks,
)
