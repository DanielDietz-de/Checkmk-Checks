#!/usr/bin/env python3
"""Health-score check for Dell EMC Unisphere PowerMax systems."""

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Metric,
    Result,
    Service,
    State,
    check_levels,
)

from .utils import parse_section


agent_section_unisphere_powermax_health_score = AgentSection(
    name="unisphere_powermax_health_score",
    parse_function=parse_section,
)


def discover_health(section):
    for item in section:
        yield Service(item=item)


def check_health(item, params, section):
    data = section.get(item)
    if data is None:
        yield Result(state=State.UNKNOWN, summary="Item is missing from agent data")
        return

    score = data.get("health_score")
    if score is None:
        yield Result(state=State.UNKNOWN, summary="No health score received from agent")
        return

    numeric_score = float(score)
    levels = params["levels"]
    yield from check_levels(
        numeric_score,
        levels_lower=levels,
        label="Health Score",
        render_func=lambda value: f"{value:.1f}",
    )
    yield Metric(
        name="health_score",
        value=numeric_score,
        levels=levels[1] if levels[0] == "fixed" else None,
        boundaries=(0.0, 100.0),
    )


check_plugin_unisphere_powermax_health_score = CheckPlugin(
    name="unisphere_powermax_health_score",
    service_name="Health Score %s",
    discovery_function=discover_health,
    check_function=check_health,
    check_ruleset_name="unisphere_powermax_health_score",
    check_default_parameters={"levels": ("fixed", (90.0, 80.0))},
)
