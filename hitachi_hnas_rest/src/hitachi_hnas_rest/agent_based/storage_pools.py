#!/usr/bin/env python3
"""
Hitachi HNAS Storage Pools

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


def parse_hitachi_hnas_rest_storage_pools(string_table):
    """
    One JSON object per line, keyed by storage pool label
    """
    parsed = {}
    for line in string_table:
        try:
            data = json.loads(line[0])
            parsed[data["label"]] = data
        except (json.JSONDecodeError, KeyError):
            continue
    return parsed


agent_section_hitachi_hnas_rest_storage_pools = AgentSection(
    name="hitachi_hnas_rest_storage_pools",
    parse_function=parse_hitachi_hnas_rest_storage_pools,
)


def discover_hitachi_hnas_rest_storage_pools(section):
    for label in section:
        yield Service(item=label)


def check_hitachi_hnas_rest_storage_pools(item, params, section):
    pool = section.get(item)
    if not pool:
        return

    capacity = pool.get("totalCapacity") or 0
    used = pool.get("usedCapacity") or 0

    if capacity:
        yield from check_levels(
            used * 100.0 / capacity,
            levels_upper=params.get("levels_used"),
            metric_name="hnas_pool_used_percent",
            render_func=render.percent,
            boundaries=(0.0, 100.0),
            label="Used",
        )
        yield Result(
            state=State.OK,
            summary=f"{render.disksize(used)} of {render.disksize(capacity)}",
        )
        yield Metric("hnas_pool_used", used, boundaries=(0, capacity))
        yield Metric("hnas_pool_size", capacity)

    is_healthy = pool.get("isHealthy")
    if is_healthy is False:
        yield Result(state=State.CRIT, summary="Pool is not healthy")
    elif is_healthy:
        yield Result(state=State.OK, notice="Pool is healthy")


check_plugin_hitachi_hnas_rest_storage_pools = CheckPlugin(
    name="hitachi_hnas_rest_storage_pools",
    sections=["hitachi_hnas_rest_storage_pools"],
    service_name="HNAS Storage Pool %s",
    discovery_function=discover_hitachi_hnas_rest_storage_pools,
    check_function=check_hitachi_hnas_rest_storage_pools,
    check_ruleset_name="hitachi_hnas_rest_storage_pools",
    check_default_parameters={
        "levels_used": ("fixed", (80.0, 90.0)),
    },
)
