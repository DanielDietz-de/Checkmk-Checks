#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from time import time

from cmk.agent_based.v2 import (
    CheckPlugin,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    all_of,
    check_levels,
    exists,
    get_value_store,
    startswith,
)
from cmk.agent_based.v2.render import timespan


def parse_palo_alto_urlfilter(string_table):
    if not string_table or not string_table[0]:
        return None
    return string_table[0][0]


snmp_section_palo_alto_urlfilter = SimpleSNMPSection(
    name="palo_alto_urlfilter",
    parse_function=parse_palo_alto_urlfilter,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25461.2.1.2.1",
        oids=["10"],
    ),
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", "Palo Alto"),
        exists(".1.3.6.1.4.1.25461.2.1.2.5.1.*"),
    ),
)


def discover_palo_alto_urlfilter(section):
    yield Service()


def check_palo_alto_urlfilter(params, section):
    value_store = get_value_store()
    now = time()

    version = section
    last_version = value_store.get('last_version', version)
    if last_version != version:
        value_store['last_update'] = now
    value_store['last_version'] = version

    yield Result(
        state=State.OK,
        summary=f"Current Version: {version}",
    )

    last_update = value_store.get('last_update', now)
    if last_update == now:
        value_store['last_update'] = now
    timediff = now - last_update

    yield from check_levels(
        value=timediff,
        levels_upper=params["age"],
        render_func=timespan,
        label="Age",
    )


check_plugin_palo_alto_urlfilter = CheckPlugin(
    name="palo_alto_urlfilter",
    service_name="Palo Alto URL-Filtering Version",
    discovery_function=discover_palo_alto_urlfilter,
    check_function=check_palo_alto_urlfilter,
    check_ruleset_name="palo_alto_urlfilter",
    check_default_parameters={"age": ("fixed", (86400.0, 104400.0))},
)
