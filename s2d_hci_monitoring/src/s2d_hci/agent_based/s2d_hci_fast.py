#!/usr/bin/env python3
"""Parse and evaluate fast-changing Windows S2D/HCI cluster state.

The module consumes JSON-lines sections emitted by the read-only Windows
collector and registers Check API V2 services for cluster, quorum, node,
network, group, and resource state. Malformed rows are ignored so one damaged
record does not suppress otherwise valid cluster telemetry.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Result, Service, State


@dataclass(frozen=True)
class ClusterObject:
    """Normalized cluster object retained with its original detail mapping."""

    name: str
    state: str
    details: Mapping[str, object]


Section = Mapping[str, ClusterObject]


def _parse_json_objects(string_table: Sequence[Sequence[str]], name_key: str = "name") -> Section:
    """Return valid JSON rows indexed by a stable object name."""

    parsed: dict[str, ClusterObject] = {}
    for row in string_table:
        if not row:
            continue
        try:
            data = json.loads(" ".join(row))
        except json.JSONDecodeError:
            continue
        name = str(
            data.get(name_key)
            or data.get("friendly_name")
            or data.get("quorum_type")
            or data.get("adapter")
            or data.get("resource_type")
            or data.get("section")
            or "cluster"
        )
        state = str(data.get("state") or data.get("quorum_resource_state") or data.get("success") or "unknown")
        parsed[name] = ClusterObject(name=name, state=state, details=data)
    return parsed


def _state_from_cluster_state(state: str) -> State:
    """Map Microsoft cluster state text to a conservative Checkmk state."""

    normalized = state.lower()
    if normalized in {"up", "online", "ok", "true", "succeeded"}:
        return State.OK
    if normalized in {"paused", "draining", "warning", "degraded"}:
        return State.WARN
    if normalized in {"down", "offline", "failed", "false"}:
        return State.CRIT
    return State.UNKNOWN


def _is_explicit_false(value: object) -> bool:
    """Return whether a structured collector success value explicitly means false."""

    return value is False or (isinstance(value, str) and value.strip().lower() == "false")


def _discover_items(section: Section):
    for item in section:
        yield Service(item=item)


def _check_cluster_object(item: str, section: Section, label: str):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"{label} {item!r} not found")
        return
    entry = section[item]
    yield Result(
        state=_state_from_cluster_state(entry.state),
        summary=f"State: {entry.state}",
        details=str(entry.details),
    )


def parse_s2d_hci_cluster_summary(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_json_objects(string_table)


agent_section_s2d_hci_cluster_summary = AgentSection(
    name="s2d_hci_cluster_summary",
    parse_function=parse_s2d_hci_cluster_summary,
)


def discover_s2d_hci_cluster_summary(section: Section):
    for item in section:
        yield Service(item=item)


def check_s2d_hci_cluster_summary(item: str, section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Cluster summary {item!r} not found")
        return
    entry = section[item]
    if entry.state.lower() in {"false", "failed"}:
        state = State.CRIT
    else:
        state = State.OK
    yield Result(
        state=state,
        summary=f"Cluster: {entry.name}, owner: {entry.details.get('owner_node', 'n/a')}",
        details=str(entry.details),
    )


check_plugin_s2d_hci_cluster_summary = CheckPlugin(
    name="s2d_hci_cluster_summary",
    service_name="S2D/HCI cluster %s",
    discovery_function=discover_s2d_hci_cluster_summary,
    check_function=check_s2d_hci_cluster_summary,
)


def parse_s2d_hci_nodes(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_json_objects(string_table)


agent_section_s2d_hci_nodes = AgentSection(name="s2d_hci_nodes", parse_function=parse_s2d_hci_nodes)


def discover_s2d_hci_nodes(section: Section):
    for item in section:
        yield Service(item=item)


def check_s2d_hci_nodes(item: str, section: Section):
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Node {item!r} not found")
        return
    entry = section[item]
    drain_status = entry.details.get("drain_status")
    state = _state_from_cluster_state(entry.state)
    if state is State.OK and str(drain_status).lower() not in {"notinitiated", "none", "0", ""}:
        state = State.WARN
    yield Result(state=state, summary=f"State: {entry.state}, drain: {drain_status}", details=str(entry.details))


check_plugin_s2d_hci_nodes = CheckPlugin(
    name="s2d_hci_nodes",
    service_name="S2D/HCI node %s",
    discovery_function=discover_s2d_hci_nodes,
    check_function=check_s2d_hci_nodes,
)


def parse_s2d_hci_networks(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_json_objects(string_table)


agent_section_s2d_hci_networks = AgentSection(name="s2d_hci_networks", parse_function=parse_s2d_hci_networks)


def discover_s2d_hci_networks(section: Section):
    for item in section:
        yield Service(item=item)


def check_s2d_hci_networks(item: str, section: Section):
    yield from _check_cluster_object(item, section, "Network")


check_plugin_s2d_hci_networks = CheckPlugin(
    name="s2d_hci_networks",
    service_name="S2D/HCI network %s",
    discovery_function=discover_s2d_hci_networks,
    check_function=check_s2d_hci_networks,
)


def parse_s2d_hci_network_interfaces(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_json_objects(string_table)


agent_section_s2d_hci_network_interfaces = AgentSection(
    name="s2d_hci_network_interfaces",
    parse_function=parse_s2d_hci_network_interfaces,
)


def discover_s2d_hci_network_interfaces(section: Section):
    yield from _discover_items(section)


def check_s2d_hci_network_interfaces(item: str, section: Section):
    yield from _check_cluster_object(item, section, "Network interface")


check_plugin_s2d_hci_network_interfaces = CheckPlugin(
    name="s2d_hci_network_interfaces",
    service_name="S2D/HCI network interface %s",
    discovery_function=discover_s2d_hci_network_interfaces,
    check_function=check_s2d_hci_network_interfaces,
)


def parse_s2d_hci_cluster_groups(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_json_objects(string_table)


agent_section_s2d_hci_cluster_groups = AgentSection(
    name="s2d_hci_cluster_groups",
    parse_function=parse_s2d_hci_cluster_groups,
)


def discover_s2d_hci_cluster_groups(section: Section):
    yield from _discover_items(section)


def check_s2d_hci_cluster_groups(item: str, section: Section):
    yield from _check_cluster_object(item, section, "Cluster group")


check_plugin_s2d_hci_cluster_groups = CheckPlugin(
    name="s2d_hci_cluster_groups",
    service_name="S2D/HCI cluster group %s",
    discovery_function=discover_s2d_hci_cluster_groups,
    check_function=check_s2d_hci_cluster_groups,
)


def parse_s2d_hci_cluster_resources(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_json_objects(string_table)


agent_section_s2d_hci_cluster_resources = AgentSection(
    name="s2d_hci_cluster_resources",
    parse_function=parse_s2d_hci_cluster_resources,
)


def discover_s2d_hci_cluster_resources(section: Section):
    yield from _discover_items(section)


def check_s2d_hci_cluster_resources(item: str, section: Section):
    yield from _check_cluster_object(item, section, "Cluster resource")


check_plugin_s2d_hci_cluster_resources = CheckPlugin(
    name="s2d_hci_cluster_resources",
    service_name="S2D/HCI cluster resource %s",
    discovery_function=discover_s2d_hci_cluster_resources,
    check_function=check_s2d_hci_cluster_resources,
)


def parse_s2d_hci_quorum(string_table: Sequence[Sequence[str]]) -> Section:
    return _parse_json_objects(string_table, name_key="quorum_type")


agent_section_s2d_hci_quorum = AgentSection(name="s2d_hci_quorum", parse_function=parse_s2d_hci_quorum)


def discover_s2d_hci_quorum(section: Section):
    if section:
        yield Service()


def check_s2d_hci_quorum(section: Section):
    if not section:
        yield Result(state=State.UNKNOWN, summary="No quorum data found")
        return
    entry = next(iter(section.values()))
    if _is_explicit_false(entry.details.get("success")):
        error = str(entry.details.get("error") or "unknown collector error")
        yield Result(
            state=State.UNKNOWN,
            summary=f"Quorum collection failed: {error}",
            details=str(entry.details),
        )
        return
    resource_state = str(entry.details.get("quorum_resource_state") or "")
    state = State.OK if resource_state.lower() in {"online", "", "none"} else State.CRIT
    yield Result(state=state, summary=f"Quorum type: {entry.name}, resource state: {resource_state or 'n/a'}", details=str(entry.details))


check_plugin_s2d_hci_quorum = CheckPlugin(
    name="s2d_hci_quorum",
    service_name="S2D/HCI quorum",
    discovery_function=discover_s2d_hci_quorum,
    check_function=check_s2d_hci_quorum,
)
