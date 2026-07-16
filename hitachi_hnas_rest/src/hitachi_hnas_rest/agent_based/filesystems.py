#!/usr/bin/env python3
"""
Hitachi HNAS Filesystems

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
    check_levels,
    render,
)


def parse_hitachi_hnas_rest_filesystems(string_table):
    """
    One JSON object per line, keyed by filesystem label
    """
    parsed = {}
    for line in string_table:
        try:
            data = json.loads(line[0])
            parsed[data["label"]] = data
        except (json.JSONDecodeError, KeyError):
            continue
    return parsed


agent_section_hitachi_hnas_rest_filesystems = AgentSection(
    name="hitachi_hnas_rest_filesystems",
    parse_function=parse_hitachi_hnas_rest_filesystems,
)


def discover_hitachi_hnas_rest_filesystems(section):
    for label in section:
        yield Service(item=label)


def check_hitachi_hnas_rest_filesystems(item, params, section):
    filesystem = section.get(item)
    if not filesystem:
        return

    status = filesystem.get("status")
    if status != "MOUNTED":
        yield Result(
            state=State(params["state_not_mounted"]),
            summary=f"Status: {status}",
        )
        return

    capacity = filesystem.get("capacity") or 0
    used = filesystem.get("usedCapacity") or 0

    if capacity:
        yield from check_levels(
            used * 100.0 / capacity,
            levels_upper=params.get("levels_used"),
            metric_name="hnas_fs_used_percent",
            render_func=render.percent,
            boundaries=(0.0, 100.0),
            label="Used",
        )
        yield Result(
            state=State.OK,
            summary=f"{render.disksize(used)} of {render.disksize(capacity)}",
        )
        yield Metric("hnas_fs_used", used, boundaries=(0, capacity))
        yield Metric("hnas_fs_size", capacity)

    snapshot_used = filesystem.get("usedSnapshotCapacity")
    if snapshot_used is not None:
        yield Result(
            state=State.OK,
            notice=f"Used by snapshots: {render.disksize(snapshot_used)}",
        )
        yield Metric("hnas_fs_snapshot_used", snapshot_used)

    tp_enabled = filesystem.get("isThinProvisioningEnabled")
    tp_valid = filesystem.get("isThinProvisioningEnabledValid")
    if tp_enabled and tp_valid:
        yield Result(state=State.OK, notice="Thin provisioning: enabled")
    elif tp_enabled and not tp_valid:
        yield Result(
            state=State(params["state_tp_invalid"]),
            summary="Thin provisioning enabled but not valid",
        )
    else:
        yield Result(
            state=State(params["state_tp_disabled"]),
            notice="Thin provisioning not enabled",
        )

    if filesystem.get("isReadOnly"):
        yield Result(state=State.OK, notice="Filesystem is read-only")


check_plugin_hitachi_hnas_rest_filesystems = CheckPlugin(
    name="hitachi_hnas_rest_filesystems",
    sections=["hitachi_hnas_rest_filesystems"],
    service_name="HNAS Filesystem %s",
    discovery_function=discover_hitachi_hnas_rest_filesystems,
    check_function=check_hitachi_hnas_rest_filesystems,
    check_ruleset_name="hitachi_hnas_rest_filesystems",
    check_default_parameters={
        "levels_used": ("fixed", (80.0, 90.0)),
        "state_not_mounted": 1,
        "state_tp_invalid": 1,
        "state_tp_disabled": 0,
    },
)
