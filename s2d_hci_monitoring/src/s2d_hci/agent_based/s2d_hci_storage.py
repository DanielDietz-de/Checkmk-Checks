#!/usr/bin/env python3
"""Monitor S2D storage capacity and health using stable collector identities."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Metric, Result, State, check_levels

from .s2d_hci_protocol import (
    DEFAULT_STATE_POLICY,
    Section,
    as_float,
    collector_error,
    discover_items,
    parse_protocol_objects,
    state_from_text,
)

STATE_DEFAULTS = dict(DEFAULT_STATE_POLICY)
FREE_SPACE_DEFAULTS: Mapping[str, object] = {
    "levels_lower_free": ("fixed", (15.0, 10.0)),
    **STATE_DEFAULTS,
}


def _parse_storage(
    string_table: Sequence[Sequence[str]],
    *,
    display_fields: Sequence[str],
    state_fields: Sequence[str] = ("health_status", "state", "operational_status"),
    fallback_name: str,
) -> Section:
    """Parse one storage section with protocol, identity, and duplicate validation."""

    return parse_protocol_objects(
        string_table,
        identity_fields=("identity", "name", "friendly_name", "section"),
        display_fields=display_fields,
        state_fields=state_fields,
        fallback_name=fallback_name,
    )


def _storage_result(item: str, params: Mapping[str, object], section: Section, label: str):
    """Return the normalized storage object and its conservative health result."""

    entry = section.get(item)
    if entry is None:
        return None, Result(state=State.UNKNOWN, summary=f"{label} {item!r} not found")
    error = collector_error(entry)
    if error:
        return entry, Result(state=State.UNKNOWN, summary=f"{label} collection failed: {error}", details=str(entry.details))
    operational = str(entry.details.get("operational_status") or "")
    combined = f"{entry.state} {operational}".strip()
    return entry, Result(
        state=state_from_text(combined, params),
        summary=f"{label}: {entry.name}, health: {entry.state}, operational: {operational or 'n/a'}",
        details=str(entry.details),
    )


def parse_s2d_hci_csv(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse Cluster Shared Volumes using stable collector identities."""

    return _parse_storage(string_table, display_fields=("name",), fallback_name="CSV")


agent_section_s2d_hci_csv = AgentSection(name="s2d_hci_csv", parse_function=parse_s2d_hci_csv)


def discover_s2d_hci_csv(section: Section):
    """Discover Cluster Shared Volume services and preserve synthetic protocol errors as separate operator-visible services."""

    yield from discover_items(section)


def check_s2d_hci_csv(item: str, params: Mapping[str, object], section: Section):
    """Evaluate Cluster Shared Volume health and apply configurable lower free-space thresholds when a finite metric is available."""

    entry, health_result = _storage_result(item, params, section, "CSV")
    if entry is None or collector_error(entry):
        yield health_result
        return
    percent_free = as_float(entry.details.get("percent_free"))
    if percent_free is not None:
        yield from check_levels(
            percent_free,
            levels_lower=params.get("levels_lower_free", ("fixed", (15.0, 10.0))),
            metric_name="s2d_hci_percent_free",
            label="Free space",
            render_func=lambda value: f"{value:.2f}%",
            boundaries=(0.0, 100.0),
        )
    yield health_result


check_plugin_s2d_hci_csv = CheckPlugin(
    name="s2d_hci_csv",
    service_name="S2D/HCI CSV %s",
    discovery_function=discover_s2d_hci_csv,
    check_function=check_s2d_hci_csv,
    check_default_parameters=FREE_SPACE_DEFAULTS,
    check_ruleset_name="s2d_hci_csv",
)


def parse_s2d_hci_storage_pools(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse storage pools using opaque stable identities and readable summaries."""

    return _parse_storage(string_table, display_fields=("friendly_name", "name"), fallback_name="Storage pool")


agent_section_s2d_hci_storage_pools = AgentSection(name="s2d_hci_storage_pools", parse_function=parse_s2d_hci_storage_pools)


def discover_s2d_hci_storage_pools(section: Section):
    """Discover one service for every stable storage-pool identity and any synthetic protocol-validation failure."""

    yield from discover_items(section)


def check_s2d_hci_storage_pools(item: str, params: Mapping[str, object], section: Section):
    """Evaluate storage pool health and emit allocated-capacity metrics."""

    entry, result = _storage_result(item, params, section, "Storage pool")
    if entry is None or collector_error(entry):
        yield result
        return
    allocated = as_float(entry.details.get("allocated_size"))
    if allocated is not None:
        yield Metric("s2d_hci_pool_allocated_bytes", allocated)
    yield result


check_plugin_s2d_hci_storage_pools = CheckPlugin(
    name="s2d_hci_storage_pools",
    service_name="S2D/HCI storage pool %s",
    discovery_function=discover_s2d_hci_storage_pools,
    check_function=check_s2d_hci_storage_pools,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)


def parse_s2d_hci_virtual_disks(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse Storage Spaces virtual disks using stable identities."""

    return _parse_storage(string_table, display_fields=("friendly_name", "name"), fallback_name="Virtual disk")


agent_section_s2d_hci_virtual_disks = AgentSection(name="s2d_hci_virtual_disks", parse_function=parse_s2d_hci_virtual_disks)


def discover_s2d_hci_virtual_disks(section: Section):
    """Discover Storage Spaces virtual-disk services without discarding malformed, duplicate, or failed collector records."""

    yield from discover_items(section)


def check_s2d_hci_virtual_disks(item: str, params: Mapping[str, object], section: Section):
    """Evaluate virtual-disk health, treating detach reasons as critical."""

    entry, result = _storage_result(item, params, section, "Virtual disk")
    if entry is None or collector_error(entry):
        yield result
        return
    if entry.details.get("detached_reason"):
        yield Result(state=State.CRIT, summary=f"Virtual disk {entry.name} is detached: {entry.details.get('detached_reason')}", details=str(entry.details))
        return
    yield result


check_plugin_s2d_hci_virtual_disks = CheckPlugin(
    name="s2d_hci_virtual_disks",
    service_name="S2D/HCI virtual disk %s",
    discovery_function=discover_s2d_hci_virtual_disks,
    check_function=check_s2d_hci_virtual_disks,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)


def parse_s2d_hci_volumes(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse volumes using the collector's duplicate-safe composite identity."""

    return _parse_storage(
        string_table,
        display_fields=("filesystem_label", "drive_letter", "name"),
        fallback_name="Volume",
    )


agent_section_s2d_hci_volumes = AgentSection(name="s2d_hci_volumes", parse_function=parse_s2d_hci_volumes)


def discover_s2d_hci_volumes(section: Section):
    """Discover volume services without collapsing duplicate filesystem labels."""

    yield from discover_items(section)


def check_s2d_hci_volumes(item: str, params: Mapping[str, object], section: Section):
    """Evaluate volume health and apply lower free-space thresholds while preserving duplicate-safe collector identities."""

    entry, result = _storage_result(item, params, section, "Volume")
    if entry is None or collector_error(entry):
        yield result
        return
    percent_free = as_float(entry.details.get("percent_free"))
    if percent_free is not None:
        yield from check_levels(
            percent_free,
            levels_lower=params.get("levels_lower_free", ("fixed", (15.0, 10.0))),
            metric_name="s2d_hci_volume_percent_free",
            label="Free space",
            render_func=lambda value: f"{value:.2f}%",
            boundaries=(0.0, 100.0),
        )
    yield result


check_plugin_s2d_hci_volumes = CheckPlugin(
    name="s2d_hci_volumes",
    service_name="S2D/HCI volume %s",
    discovery_function=discover_s2d_hci_volumes,
    check_function=check_s2d_hci_volumes,
    check_default_parameters=FREE_SPACE_DEFAULTS,
    check_ruleset_name="s2d_hci_volumes",
)


def parse_s2d_hci_physical_disks(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse physical-disk records using privacy-preserving stable identities so raw serials or unique IDs need not become service keys."""

    return _parse_storage(string_table, display_fields=("friendly_name", "name"), fallback_name="Physical disk")


agent_section_s2d_hci_physical_disks = AgentSection(name="s2d_hci_physical_disks", parse_function=parse_s2d_hci_physical_disks)


def discover_s2d_hci_physical_disks(section: Section):
    """Discover one service for each privacy-preserving physical-disk identity and each synthetic protocol-error record."""

    yield from discover_items(section)


def check_s2d_hci_physical_disks(item: str, params: Mapping[str, object], section: Section):
    """Evaluate physical-disk health and operational usage through the configured conservative state policy."""

    _entry, result = _storage_result(item, params, section, "Physical disk")
    yield result


check_plugin_s2d_hci_physical_disks = CheckPlugin(
    name="s2d_hci_physical_disks",
    service_name="S2D/HCI physical disk %s",
    discovery_function=discover_s2d_hci_physical_disks,
    check_function=check_s2d_hci_physical_disks,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)
