#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from cmk.agent_based.v2 import (
    Service,
    Result,
    State,
    Metric,
    SimpleSNMPSection,
    SNMPTree,
    exists,
    CheckPlugin,
)

class SidecoolerSupply():
    """Represent sidecoolersupply behavior and associated state."""
    devices: dict

    def __init__(self, a, b):
        """Initialize the instance and its required state."""
        self.devices = {
            "A": a,
            "B": b,
        }


def parse_sidecooler_supply(string_table):
    """Parse sidecooler supply into its normalized representation."""
    if not string_table:
        return None

    snmp_data = [s for s in string_table[0]]

    return SidecoolerSupply(*snmp_data)


def discover_sidecooler_supply(section):
    """Discover sidecooler supply from the available input data."""
    for supply in section.devices.keys():
        yield Service(item=supply)


def check_sidecooler_supply(item, section):
    """Evaluate sidecooler supply and return its resulting state."""
    supply_state = {
        "0": "inactive",
        "1": "ok",
        "2": "failture",
    }

    if item not in section.devices.keys():
        yield Result(state=State.UNKNOWN, summary="Item not found")

    if section.devices[item] == "2":
        yield Result(state=State.CRIT, summary=f"State: {supply_state[section.devices[item]]}")
    else:
        yield Result(state=State.OK, summary=f"State: {supply_state[section.devices[item]]}")


snmp_section_sidecooler_supply = SimpleSNMPSection(
    name = "sidecooler_supply",
    parse_function = parse_sidecooler_supply,
    fetch = SNMPTree(
        base = ".1.3.6.1.4.1.46984.17.3",
        oids = [
            "122",   # SideCoolerMib::powerStateA
            "123",   # SideCoolerMib::powerStateB
        ],
    ),
    detect = exists(".1.3.6.1.4.1.46984.17.3.*"),
)


check_plugin_sidecooler_supply = CheckPlugin(
    name="sidecooler_supply",
    service_name="Sidecooler Supply %s",
    discovery_function=discover_sidecooler_supply,
    check_function=check_sidecooler_supply,
)
