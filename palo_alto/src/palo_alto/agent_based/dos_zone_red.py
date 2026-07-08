#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from time import time

from cmk.agent_based.v2 import (
    CheckPlugin,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    all_of,
    check_levels,
    exists,
    get_rate,
    get_value_store,
    startswith,
)


def parse_palo_alto_dos_zone_red(string_table):
    if not string_table or not string_table[0]:
        return None
    activate, maximum = string_table[0]
    return {"activate": int(activate), "maximum": int(maximum)}


snmp_section_palo_alto_dos_zone_red = SimpleSNMPSection(
    name="palo_alto_dos_zone_red",
    parse_function=parse_palo_alto_dos_zone_red,
    fetch=SNMPTree(
        # panFlowDosZoneRedAct (.31) / panFlowDosZoneRedMax (.32)
        base=".1.3.6.1.4.1.25461.2.1.2.1.19.8",
        oids=["31", "32"],
    ),
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", "Palo Alto"),
        exists(".1.3.6.1.4.1.25461.2.1.2.1.19.8.31.0"),
    ),
)


def discover_palo_alto_dos_zone_red(section):
    yield Service()


def check_palo_alto_dos_zone_red(params, section):
    value_store = get_value_store()
    now = time()

    for key, label, metric_name, levels_key in (
        ("activate", "Activate", "palo_alto_dos_zone_red_activate", "levels_activate"),
        ("maximum", "Maximum", "palo_alto_dos_zone_red_maximum", "levels_maximum"),
    ):
        # get_rate raises GetRateError (a subclass of IgnoreResultsError) on the
        # first evaluation, which Checkmk turns into an "initializing" message.
        rate = get_rate(value_store, key, now, section[key])
        yield from check_levels(
            value=rate,
            levels_upper=params[levels_key],
            metric_name=metric_name,
            render_func=lambda v: f"{v:.2f} pkts/s",
            label=f"{label} drops",
        )


check_plugin_palo_alto_dos_zone_red = CheckPlugin(
    name="palo_alto_dos_zone_red",
    service_name="Palo Alto DoS Zone RED Drops",
    discovery_function=discover_palo_alto_dos_zone_red,
    check_function=check_palo_alto_dos_zone_red,
    check_ruleset_name="palo_alto_dos_zone_red",
    check_default_parameters={
        "levels_activate": ("no_levels", None),
        "levels_maximum": ("no_levels", None),
    },
)
