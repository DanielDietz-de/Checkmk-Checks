"""
ERA NTP server table (OID branch .115.4 = ntpTable).
"""
from .utils import detect_era, era_state
from cmk.agent_based.v2 import (
    SNMPTree,
    CheckPlugin,
    SNMPSection,
    Service,
    Result,
    OIDEnd,
)


def parse_era_ntp(string_table):
    """Parse era ntp into its normalized representation."""
    section = {}
    for entry in string_table[0]:
        oid_end, status = entry
        if not status:
            continue
        section[oid_end] = status
    return section


def discover_era_ntp(section):
    """Discover era ntp from the available input data."""
    for item in section:
        yield Service(item=item)


def check_era_ntp(item, section):
    """Evaluate era ntp and return its resulting state."""
    status = section.get(item)
    if status is None:
        return
    yield Result(state=era_state(status), summary=f"Status: {status}")


snmp_section_era_ntp = SNMPSection(
    name="era_ntp",
    detect=detect_era,
    parse_function=parse_era_ntp,
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.11588.1.5.115.4.1',
            oids=[
                OIDEnd(),
                '2',  # ntpStatus
            ],
        ),
    ],
)


check_plugin_era_ntp = CheckPlugin(
    name='era_ntp',
    service_name='ERA NTP %s',
    discovery_function=discover_era_ntp,
    check_function=check_era_ntp,
)
