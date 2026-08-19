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

class SidecoolerStatus():
    """Represent sidecoolerstatus behavior and associated state."""
    device: str
    vendor: str
    sw_version: int
    device_type: str
    operating_hours: int

    def __init__(self, device, vendor, sw_version, device_type, operating_hours):
        """Initialize the instance and its required state."""
        self.device = device
        self.vendor = vendor
        self.sw_version = int(sw_version)
        self.device_type = device_type
        self.operating_hours = int(operating_hours)


def parse_sidecooler_status(string_table):
    """Parse sidecooler status into its normalized representation."""
    if not string_table:
        return None

    snmp_data = [s for s in string_table[0]]

    return SidecoolerStatus(*snmp_data)


def discover_sidecooler_status(section):
    """Discover sidecooler status from the available input data."""
    yield Service()


def check_sidecooler_status(section):
    """Evaluate sidecooler status and return its resulting state."""
    yield Metric("uptime", section.operating_hours*3600)

    text = f"Device: {section.device}, Vendor name: {section.vendor}, Software version: {section.sw_version}, Device type: {section.device_type}, Operating hours: {section.operating_hours}"

    yield Result(state=State.OK, summary=text)


snmp_section_sidecooler_status = SimpleSNMPSection(
    name = "sidecooler_status",
    parse_function = parse_sidecooler_status,
    fetch = SNMPTree(
        base = ".1.3.6.1.4.1.46984.17.1",
        oids = [
            "1",   # SideCoolerMib::device
            "2",   # SideCoolerMib::vendor
            "3",   # SideCoolerMib::swVersion
            "4",   # SideCoolerMib::deviceType
            "5"    # SideCoolerMib::operationhoures
        ],
    ),
    detect = exists(".1.3.6.1.4.1.46984.17.1.*"),
)


check_plugin_sidecooler_status = CheckPlugin(
    name = "sidecooler_status",
    service_name = "Sidecooler status",
    discovery_function = discover_sidecooler_status,
    check_function = check_sidecooler_status,
)
