#!/usr/bin/env python3
"""
Hitachi HNAS Cluster Nodes

Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""
import json

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Metric,
    Result,
    Service,
    State,
    render,
)


def parse_hitachi_hnas_rest_nodes(string_table):
    """
    One JSON object per line, keyed by node name
    """
    parsed = {}
    for line in string_table:
        try:
            data = json.loads(line[0])
            parsed[data["name"]] = data
        except (json.JSONDecodeError, KeyError):
            continue
    return parsed


agent_section_hitachi_hnas_rest_nodes = AgentSection(
    name="hitachi_hnas_rest_nodes",
    parse_function=parse_hitachi_hnas_rest_nodes,
)


def discover_hitachi_hnas_rest_nodes(section):
    for name in section:
        yield Service(item=name)


def check_hitachi_hnas_rest_nodes(item, section):
    node = section.get(item)
    if not node:
        return

    status = node.get("status", "UNKNOWN")
    yield Result(
        state=State.OK if status == "ONLINE" else State.CRIT,
        summary=f"Status: {status}",
    )

    if node.get("model"):
        yield Result(state=State.OK, summary=f"Model: {node['model']}")

    if node.get("firmwareVersion"):
        yield Result(state=State.OK, summary=f"Firmware: {node['firmwareVersion']}")

    uptime = node.get("uptimeInSeconds")
    if uptime is not None:
        yield Result(state=State.OK, notice=f"Uptime: {render.timespan(uptime)}")
        yield Metric("uptime", uptime)


check_plugin_hitachi_hnas_rest_nodes = CheckPlugin(
    name="hitachi_hnas_rest_nodes",
    sections=["hitachi_hnas_rest_nodes"],
    service_name="HNAS Node %s",
    discovery_function=discover_hitachi_hnas_rest_nodes,
    check_function=check_hitachi_hnas_rest_nodes,
)
