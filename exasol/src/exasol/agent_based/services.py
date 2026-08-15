#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    check_levels,
    Result,
    Service,
    State,
)

def parse_exasol_services(string_table):
    """Parse exasol services into its normalized representation."""
    services = {}

    for service, state in string_table:
        services[service] = state

    return services


agent_section_exasol_services = AgentSection(
    name = "exasol_services",
    parse_function = parse_exasol_services,
)


def discover_exasol_services(section):
    """Discover exasol services from the available input data."""
    yield Service()


def check_exasol_services(section):
    """Evaluate exasol services and return its resulting state."""
    for service, state in section.items():
        text = f"{service}: {state}"

        if "OK" != state:
            yield Result(state=State.CRIT, summary=text)

        else:
            yield Result(state=State.OK, summary=text)


check_plugin_exasol_services = CheckPlugin(
    name = "exasol_services",
    sections = ["exasol_services"],
    service_name = "Services",
    discovery_function = discover_exasol_services,
    check_function = check_exasol_services,
)
