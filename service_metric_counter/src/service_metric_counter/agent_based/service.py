#!/usr/bin/env python3
"""Check plug-in for aggregated service metrics."""

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Service, check_levels


Section = dict[str, dict[str, float | str]]


def parse_function(string_table: list[list[str]]) -> Section:
    parsed: Section = {}
    for line in string_table:
        if len(line) < 4:
            continue
        parsed[line[0]] = {
            "value": float(line[1]),
            "metric": line[2],
            "label": line[3],
        }
    return parsed


def discover_service(section: Section):
    for service_id in section:
        yield Service(item=service_id)


def check_service(item: str, params: dict, section: Section):
    data = section.get(item)
    if data is None:
        return

    yield from check_levels(
        float(data["value"]),
        levels_upper=params.get("levels", ("no_levels", None)),
        label=str(data["label"]),
        metric_name=str(data["metric"]),
    )


agent_section_service_metric_counter = AgentSection(
    name="service_metric_counter",
    parse_function=parse_function,
)


check_plugin_service_metric_counter = CheckPlugin(
    name="service_metric_counter",
    sections=["service_metric_counter"],
    service_name="Service %s",
    discovery_function=discover_service,
    check_function=check_service,
    check_default_parameters={"levels": ("no_levels", None)},
    check_ruleset_name="service_metric_counter",
)
