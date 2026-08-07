#!/usr/bin/env python3
"""Monitor fast-changing Failover Cluster state emitted by the elected collector."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Result, Service, State

from .s2d_hci_protocol import (
    DEFAULT_STATE_POLICY,
    ProtocolObject,
    Section,
    collector_error,
    discover_items,
    parse_protocol_objects,
    state_from_text,
)


STATE_DEFAULTS = dict(DEFAULT_STATE_POLICY)


def _parse_fast(
    string_table: Sequence[Sequence[str]],
    *,
    identity_fields: Sequence[str],
    display_fields: Sequence[str],
    state_fields: Sequence[str] = ("state", "quorum_resource_state"),
    fallback_name: str,
) -> Section:
    """Parse one fast collector section using the shared versioned protocol."""

    return parse_protocol_objects(
        string_table,
        identity_fields=identity_fields,
        display_fields=display_fields,
        state_fields=state_fields,
        fallback_name=fallback_name,
    )


def _discover_summary(section: Section):
    """Discover a single summary or parser-error service for each record."""

    yield from discover_items(section)


def _check_entry(
    item: str,
    params: Mapping[str, object],
    section: Section,
    *,
    label: str,
    state_value: object | None = None,
) -> tuple[ProtocolObject | None, Result]:
    """Validate one normalized object and return its baseline Checkmk result."""

    entry = section.get(item)
    if entry is None:
        return None, Result(state=State.UNKNOWN, summary=f"{label} {item!r} not found")
    error = collector_error(entry)
    if error:
        return entry, Result(state=State.UNKNOWN, summary=f"{label} collection failed: {error}", details=str(entry.details))
    effective_state = entry.state if state_value is None else state_value
    return entry, Result(
        state=state_from_text(effective_state, params),
        summary=f"{label}: {entry.name}, state: {effective_state}",
        details=str(entry.details),
    )


def parse_s2d_hci_cluster_summary(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse cluster summary records keyed by cluster name."""

    return _parse_fast(
        string_table,
        identity_fields=("identity", "name"),
        display_fields=("name",),
        state_fields=("state", "success"),
        fallback_name="Cluster",
    )


agent_section_s2d_hci_cluster_summary = AgentSection(
    name="s2d_hci_cluster_summary",
    parse_function=parse_s2d_hci_cluster_summary,
)


def discover_s2d_hci_cluster_summary(section: Section):
    """Discover cluster summary services and any synthetic parser errors."""

    yield from _discover_summary(section)


def check_s2d_hci_cluster_summary(item: str, params: Mapping[str, object], section: Section):
    """Evaluate cluster availability while exposing collection failures as UNKNOWN."""

    entry = section.get(item)
    if entry is None:
        yield Result(state=State.UNKNOWN, summary=f"Cluster {item!r} not found")
        return
    error = collector_error(entry)
    if error:
        yield Result(state=State.UNKNOWN, summary=f"Cluster collection failed: {error}", details=str(entry.details))
        return
    yield Result(
        state=State.OK,
        summary=f"Cluster: {entry.name}, owner: {entry.details.get('owner_node', 'n/a')}",
        details=str(entry.details),
    )


check_plugin_s2d_hci_cluster_summary = CheckPlugin(
    name="s2d_hci_cluster_summary",
    service_name="S2D/HCI cluster %s",
    discovery_function=discover_s2d_hci_cluster_summary,
    check_function=check_s2d_hci_cluster_summary,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)


def parse_s2d_hci_quorum(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse quorum records while retaining structured command failures."""

    return _parse_fast(
        string_table,
        identity_fields=("identity", "quorum_type", "section"),
        display_fields=("quorum_type", "section"),
        state_fields=("quorum_resource_state", "success"),
        fallback_name="Quorum",
    )


agent_section_s2d_hci_quorum = AgentSection(name="s2d_hci_quorum", parse_function=parse_s2d_hci_quorum)


def discover_s2d_hci_quorum(section: Section):
    """Discover quorum services and explicit parser or collector failures."""

    yield from discover_items(section)


def check_s2d_hci_quorum(item: str, params: Mapping[str, object], section: Section):
    """Evaluate quorum resource state and never classify structured failures as OK."""

    entry = section.get(item)
    if entry is None:
        yield Result(state=State.UNKNOWN, summary=f"Quorum record {item!r} not found")
        return
    error = collector_error(entry)
    if error:
        yield Result(state=State.UNKNOWN, summary=f"Quorum collection failed: {error}", details=str(entry.details))
        return
    resource_state = str(entry.details.get("quorum_resource_state") or "none")
    state = State.OK if resource_state.lower() in {"online", "none", ""} else state_from_text(resource_state, params)
    yield Result(
        state=state,
        summary=f"Quorum type: {entry.name}, resource state: {resource_state}",
        details=str(entry.details),
    )


check_plugin_s2d_hci_quorum = CheckPlugin(
    name="s2d_hci_quorum",
    service_name="S2D/HCI quorum %s",
    discovery_function=discover_s2d_hci_quorum,
    check_function=check_s2d_hci_quorum,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)


def parse_s2d_hci_nodes(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse cluster nodes keyed by their stable node names."""

    return _parse_fast(
        string_table,
        identity_fields=("identity", "name"),
        display_fields=("name",),
        fallback_name="Cluster node",
    )


agent_section_s2d_hci_nodes = AgentSection(name="s2d_hci_nodes", parse_function=parse_s2d_hci_nodes)


def discover_s2d_hci_nodes(section: Section):
    """Discover cluster nodes and synthetic input-error services."""

    yield from discover_items(section)


def check_s2d_hci_nodes(item: str, params: Mapping[str, object], section: Section):
    """Evaluate node and drain state according to the configured state policy."""

    entry = section.get(item)
    if entry is None:
        yield Result(state=State.UNKNOWN, summary=f"Node {item!r} not found")
        return
    error = collector_error(entry)
    if error:
        yield Result(state=State.UNKNOWN, summary=f"Node collection failed: {error}", details=str(entry.details))
        return
    state = state_from_text(entry.state, params)
    drain = str(entry.details.get("drain_status") or "none")
    if state == State.OK and drain.lower() not in {"notinitiated", "none", "0", ""}:
        state = state_from_text("draining", params)
    yield Result(state=state, summary=f"Node: {entry.name}, state: {entry.state}, drain: {drain}", details=str(entry.details))


check_plugin_s2d_hci_nodes = CheckPlugin(
    name="s2d_hci_nodes",
    service_name="S2D/HCI node %s",
    discovery_function=discover_s2d_hci_nodes,
    check_function=check_s2d_hci_nodes,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)


def _parse_named_state(string_table: Sequence[Sequence[str]], fallback_name: str) -> Section:
    """Parse a generic named cluster object using identity when the collector supplies one."""

    return _parse_fast(
        string_table,
        identity_fields=("identity", "name", "section"),
        display_fields=("name", "section"),
        fallback_name=fallback_name,
    )


def _check_named_state(item: str, params: Mapping[str, object], section: Section, label: str):
    """Evaluate a generic cluster object with common collection-error handling."""

    _entry, result = _check_entry(item, params, section, label=label)
    yield result


def parse_s2d_hci_networks(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse cluster network state."""

    return _parse_named_state(string_table, "Cluster network")


agent_section_s2d_hci_networks = AgentSection(name="s2d_hci_networks", parse_function=parse_s2d_hci_networks)


def discover_s2d_hci_networks(section: Section):
    """Discover cluster network services."""

    yield from discover_items(section)


def check_s2d_hci_networks(item: str, params: Mapping[str, object], section: Section):
    """Evaluate cluster network operational state."""

    yield from _check_named_state(item, params, section, "Network")


check_plugin_s2d_hci_networks = CheckPlugin(
    name="s2d_hci_networks",
    service_name="S2D/HCI network %s",
    discovery_function=discover_s2d_hci_networks,
    check_function=check_s2d_hci_networks,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)


def parse_s2d_hci_network_interfaces(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse cluster network interfaces using the collector composite identity."""

    return _parse_named_state(string_table, "Cluster network interface")


agent_section_s2d_hci_network_interfaces = AgentSection(
    name="s2d_hci_network_interfaces",
    parse_function=parse_s2d_hci_network_interfaces,
)


def discover_s2d_hci_network_interfaces(section: Section):
    """Discover cluster network-interface services."""

    yield from discover_items(section)


def check_s2d_hci_network_interfaces(item: str, params: Mapping[str, object], section: Section):
    """Evaluate cluster network-interface state."""

    yield from _check_named_state(item, params, section, "Network interface")


check_plugin_s2d_hci_network_interfaces = CheckPlugin(
    name="s2d_hci_network_interfaces",
    service_name="S2D/HCI network interface %s",
    discovery_function=discover_s2d_hci_network_interfaces,
    check_function=check_s2d_hci_network_interfaces,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)


def parse_s2d_hci_cluster_groups(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse clustered role/group state."""

    return _parse_named_state(string_table, "Cluster group")


agent_section_s2d_hci_cluster_groups = AgentSection(
    name="s2d_hci_cluster_groups",
    parse_function=parse_s2d_hci_cluster_groups,
)


def discover_s2d_hci_cluster_groups(section: Section):
    """Discover cluster group services."""

    yield from discover_items(section)


def check_s2d_hci_cluster_groups(item: str, params: Mapping[str, object], section: Section):
    """Evaluate clustered role/group state."""

    yield from _check_named_state(item, params, section, "Cluster group")


check_plugin_s2d_hci_cluster_groups = CheckPlugin(
    name="s2d_hci_cluster_groups",
    service_name="S2D/HCI cluster group %s",
    discovery_function=discover_s2d_hci_cluster_groups,
    check_function=check_s2d_hci_cluster_groups,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)


def parse_s2d_hci_cluster_resources(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse clustered resource state."""

    return _parse_named_state(string_table, "Cluster resource")


agent_section_s2d_hci_cluster_resources = AgentSection(
    name="s2d_hci_cluster_resources",
    parse_function=parse_s2d_hci_cluster_resources,
)


def discover_s2d_hci_cluster_resources(section: Section):
    """Discover clustered resource services."""

    yield from discover_items(section)


def check_s2d_hci_cluster_resources(item: str, params: Mapping[str, object], section: Section):
    """Evaluate clustered resource state."""

    yield from _check_named_state(item, params, section, "Cluster resource")


check_plugin_s2d_hci_cluster_resources = CheckPlugin(
    name="s2d_hci_cluster_resources",
    service_name="S2D/HCI cluster resource %s",
    discovery_function=discover_s2d_hci_cluster_resources,
    check_function=check_s2d_hci_cluster_resources,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)
