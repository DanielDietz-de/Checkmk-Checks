#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from cmk.agent_based.v2 import (
    CheckPlugin,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    all_of,
    exists,
    startswith,
)


def parse_palo_alto_panorama(string_table):
    if not string_table or not string_table[0]:
        return None
    connected_1, connected_2 = string_table[0]
    return {"1": connected_1, "2": connected_2}


snmp_section_palo_alto_panorama = SimpleSNMPSection(
    name="palo_alto_panorama",
    parse_function=parse_palo_alto_panorama,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25461.2.1.2.4",
        oids=["1", "2"],
    ),
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", "Palo Alto"),
        exists(".1.3.6.1.4.1.25461.2.1.2.4.1.0"),
    ),
)


def discover_palo_alto_panorama(section):
    for item, connected in section.items():
        # Only create a service for Panorama slots that report a state.
        if connected:
            yield Service(item=item)


def check_palo_alto_panorama(item, params, section):
    connected = section.get(item)
    if connected is None:
        return

    if connected.strip().lower() == "connected":
        state = State.OK
    else:
        state = State(params["state_not_connected"])
    yield Result(state=state, summary=f"Status: {connected}")


check_plugin_palo_alto_panorama = CheckPlugin(
    name="palo_alto_panorama",
    service_name="Palo Alto Panorama %s availability",
    discovery_function=discover_palo_alto_panorama,
    check_function=check_palo_alto_panorama,
    check_ruleset_name="palo_alto_panorama",
    check_default_parameters={"state_not_connected": 2},
)
