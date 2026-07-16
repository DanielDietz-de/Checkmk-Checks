#!/usr/bin/env python3
"""
Hitachi HNAS Snapshots

Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""
import json
import time

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Result,
    Service,
    State,
    check_levels,
    render,
)


def parse_hitachi_hnas_rest_snapshots(string_table):
    """
    One JSON object per line, keyed by filesystem label
    """
    parsed = {}
    for line in string_table:
        try:
            data = json.loads(line[0])
            parsed[data["filesystem"]] = data
        except (json.JSONDecodeError, KeyError):
            continue
    return parsed


agent_section_hitachi_hnas_rest_snapshots = AgentSection(
    name="hitachi_hnas_rest_snapshots",
    parse_function=parse_hitachi_hnas_rest_snapshots,
)


def discover_hitachi_hnas_rest_snapshots(section):
    for filesystem in section:
        yield Service(item=filesystem)


def check_hitachi_hnas_rest_snapshots(item, params, section):
    data = section.get(item)
    if not data:
        return

    if "error" in data:
        yield Result(
            state=State.UNKNOWN,
            summary=f"Could not fetch snapshots: {data['error']}",
        )
        return

    yield from check_levels(
        data["count"],
        levels_upper=params.get("levels_count"),
        metric_name="hnas_snapshots",
        render_func=lambda value: str(int(value)),
        label="Snapshots",
    )

    now = time.time()

    oldest = data.get("oldest")
    if oldest is not None:
        yield from check_levels(
            max(now - oldest, 0),
            levels_upper=params.get("levels_age_oldest"),
            metric_name="hnas_snapshot_age_oldest",
            render_func=render.timespan,
            label="Oldest",
        )

    newest = data.get("newest")
    if newest is not None:
        yield from check_levels(
            max(now - newest, 0),
            levels_upper=params.get("levels_age_newest"),
            metric_name="hnas_snapshot_age_newest",
            render_func=render.timespan,
            label="Last snapshot",
        )


check_plugin_hitachi_hnas_rest_snapshots = CheckPlugin(
    name="hitachi_hnas_rest_snapshots",
    sections=["hitachi_hnas_rest_snapshots"],
    service_name="HNAS Snapshots %s",
    discovery_function=discover_hitachi_hnas_rest_snapshots,
    check_function=check_hitachi_hnas_rest_snapshots,
    check_ruleset_name="hitachi_hnas_rest_snapshots",
    check_default_parameters={
        "levels_count": ("no_levels", None),
        "levels_age_oldest": ("no_levels", None),
        "levels_age_newest": ("no_levels", None),
    },
)
