#!/usr/bin/env python3
"""
Hitachi HNAS Virtual Servers (EVS)

Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""
import json

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Result,
    Service,
    State,
)

STATUS_MAP = {
    "ONLINE": State.OK,
    "DISABLED": State.WARN,
    "OFFLINE": State.CRIT,
    "NOT_CONFIGURED": State.UNKNOWN,
}


def parse_hitachi_hnas_rest_virtual_servers(string_table):
    """
    One JSON object per line, keyed by virtual server name
    """
    parsed = {}
    for line in string_table:
        try:
            data = json.loads(line[0])
            parsed[data["name"]] = data
        except (json.JSONDecodeError, KeyError):
            continue
    return parsed


agent_section_hitachi_hnas_rest_virtual_servers = AgentSection(
    name="hitachi_hnas_rest_virtual_servers",
    parse_function=parse_hitachi_hnas_rest_virtual_servers,
)


def discover_hitachi_hnas_rest_virtual_servers(section):
    for name, server in section.items():
        if server.get("isEnabled"):
            yield Service(item=name)


def check_hitachi_hnas_rest_virtual_servers(item, section):
    server = section.get(item)
    if not server:
        return

    status = server.get("status", "UNKNOWN")
    yield Result(
        state=STATUS_MAP.get(status, State.UNKNOWN),
        summary=f"Status: {status}",
    )

    if not server.get("isEnabled"):
        yield Result(state=State.WARN, summary="Disabled by administrator")

    if server.get("type"):
        yield Result(state=State.OK, summary=f"Type: {server['type']}")

    if server.get("ipAddresses"):
        yield Result(
            state=State.OK,
            notice="IP addresses: {}".format(", ".join(server["ipAddresses"])),
        )


check_plugin_hitachi_hnas_rest_virtual_servers = CheckPlugin(
    name="hitachi_hnas_rest_virtual_servers",
    sections=["hitachi_hnas_rest_virtual_servers"],
    service_name="HNAS EVS %s",
    discovery_function=discover_hitachi_hnas_rest_virtual_servers,
    check_function=check_hitachi_hnas_rest_virtual_servers,
)
