#!/usr/bin/env python3
"""Check plug-in for Puppet agent execution status."""

import time
from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
    check_levels,
    render,
)

Section = Mapping[str, int]


def parse_puppet_agent(string_table: StringTable) -> Section:
    section: dict[str, int] = {}
    for line in string_table:
        if len(line) != 2:
            continue
        try:
            section[line[0].removesuffix(":")] = int(line[1])
        except ValueError:
            continue
    return section


def discover_puppet_agent(section: Section) -> DiscoveryResult:
    if "last_run" in section:
        yield Service()


_CHECKS = [
    ("events_failure", "Events Failure"),
    ("resources_changed", "Resources Changed"),
    ("resources_failed", "Resources Failed"),
    ("resources_failed_to_restart", "Resources Failed to Restart"),
    ("resources_out_of_sync", "Resources Out of Sync"),
    ("resources_restarted", "Resources Restarted"),
    ("resources_scheduled", "Resources Scheduled"),
]


def check_puppet_agent(params: Mapping, section: Section) -> CheckResult:
    if "last_run" not in section:
        return

    last_run = section["last_run"]
    last_run_state = State.OK
    last_run_levels = params.get("last_run")
    if isinstance(last_run_levels, tuple) and last_run_levels[0] == "fixed":
        offset = time.time() - last_run
        warn, crit = last_run_levels[1]
        if offset >= crit:
            last_run_state = State.CRIT
        elif offset >= warn:
            last_run_state = State.WARN
    yield Result(
        state=last_run_state,
        summary=f"Last run: {render.datetime(last_run)}",
    )

    for key, label in _CHECKS:
        if key not in section:
            continue
        yield from check_levels(
            section[key],
            levels_upper=params[key],
            metric_name=key,
            label=label,
        )


agent_section_puppet_agent = AgentSection(
    name="puppet_agent",
    parse_function=parse_puppet_agent,
)


check_plugin_puppet_agent = CheckPlugin(
    name="puppet_agent",
    service_name="Puppet Agent",
    discovery_function=discover_puppet_agent,
    check_function=check_puppet_agent,
    check_ruleset_name="puppet_agent",
    check_default_parameters={
        "last_run": ("fixed", (1600.0, 3200.0)),
        "events_failure": ("fixed", (10, 15)),
        "resources_changed": ("fixed", (10, 15)),
        "resources_failed": ("fixed", (10, 15)),
        "resources_failed_to_restart": ("fixed", (10, 15)),
        "resources_out_of_sync": ("fixed", (10, 15)),
        "resources_restarted": ("fixed", (10, 15)),
        "resources_scheduled": ("fixed", (10, 15)),
    },
)
