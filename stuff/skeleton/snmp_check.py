#!/usr/bin/env python3
"""Minimal valid Checkmk 2.x SNMP check plug-in template."""

from cmk.agent_based.v2 import (
    CheckPlugin,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
    all_of,
    contains,
)


def parse_example(string_table: StringTable) -> dict[str, str]:
    """Map the first two fetched columns to item/value pairs."""
    return {
        row[0]: row[1]
        for row in string_table
        if len(row) >= 2 and row[0]
    }


def discover_example(section: dict[str, str]):
    """Discover one service for every item returned by the device."""
    for item in section:
        yield Service(item=item)


def check_example(item: str, section: dict[str, str]):
    """Report the current value for one discovered item."""
    if item not in section:
        return
    yield Result(state=State.OK, summary=f"Value: {section[item]}")


snmp_section_example = SimpleSNMPSection(
    name="example_snmp",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "replace-with-vendor-signature"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.REPLACE_WITH_ENTERPRISE_OID",
        oids=["1", "2"],
    ),
    parse_function=parse_example,
)


check_plugin_example = CheckPlugin(
    name="example_snmp",
    service_name="Example %s",
    discovery_function=discover_example,
    check_function=check_example,
)
