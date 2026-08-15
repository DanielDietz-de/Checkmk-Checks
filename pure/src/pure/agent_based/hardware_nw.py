#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Result,
    Service,
    State,
)

from .utils.pure import (
    parse_pure_hardware,
)


agent_section_pure_hardware_nw = AgentSection(
    name="pure_hardware_nw",
    parse_function=parse_pure_hardware,
)


def discover_pure_hardware_nw(section):
    """Discover pure hardware nw from the available input data."""
    for item, data in section.items():
        if "nw_speed" in data:
            yield Service(item=item)

def check_pure_hardware_nw(item, section):
    """Evaluate pure hardware nw and return its resulting state."""
    data = section[item]

    if data["status"].lower() == "ok":
        state = State.OK
    else:
        state = State.CRIT

    yield Result(
        state=state,
        summary=f"Interface State: {data['status']}"
    )


check_plugin_pure_hardware_nw = CheckPlugin(
    name="pure_hardware_nw",
    sections=["pure_hardware"],
    service_name="Interface %s",
    discovery_function=discover_pure_hardware_nw,
    check_function=check_pure_hardware_nw,
)
