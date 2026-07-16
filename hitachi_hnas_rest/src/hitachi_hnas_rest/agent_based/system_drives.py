#!/usr/bin/env python3
"""
Hitachi HNAS System Drives

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
    render,
)


def parse_hitachi_hnas_rest_system_drives(string_table):
    """
    One JSON object per line, keyed by system drive ID
    """
    parsed = {}
    for line in string_table:
        try:
            data = json.loads(line[0])
            parsed[str(data["systemDriveId"])] = data
        except (json.JSONDecodeError, KeyError):
            continue
    return parsed


agent_section_hitachi_hnas_rest_system_drives = AgentSection(
    name="hitachi_hnas_rest_system_drives",
    parse_function=parse_hitachi_hnas_rest_system_drives,
)


def discover_hitachi_hnas_rest_system_drives(section):
    for drive_id in section:
        yield Service(item=drive_id)


def check_hitachi_hnas_rest_system_drives(item, section):
    drive = section.get(item)
    if not drive:
        return

    status = drive.get("status", "UNKNOWN")
    yield Result(
        state=State.OK if status == "OK" else State.CRIT,
        summary=f"Status: {status}",
    )

    if drive.get("isDegraded"):
        yield Result(state=State.CRIT, summary="Drive is degraded")

    if drive.get("label"):
        yield Result(state=State.OK, summary=f"Label: {drive['label']}")

    capacity = drive.get("capacity")
    if capacity is not None:
        yield Result(state=State.OK, summary=f"Capacity: {render.disksize(capacity)}")

    if drive.get("isAccessAllowed") is False:
        yield Result(state=State.WARN, summary="Access not allowed")


check_plugin_hitachi_hnas_rest_system_drives = CheckPlugin(
    name="hitachi_hnas_rest_system_drives",
    sections=["hitachi_hnas_rest_system_drives"],
    service_name="HNAS System Drive %s",
    discovery_function=discover_hitachi_hnas_rest_system_drives,
    check_function=check_hitachi_hnas_rest_system_drives,
)
