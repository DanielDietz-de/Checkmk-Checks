#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from cmk.agent_based.v2 import (
    CheckPlugin,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    all_of,
    check_levels,
    exists,
    render,
    startswith,
)


def parse_palo_alto_sessions(string_table):
    if not string_table or not string_table[0]:
        return None
    utilization, maximum, active, tcp, udp, icmp = string_table[0]
    return {
        "utilization": int(utilization),
        "max": int(maximum),
        "active": int(active),
        "tcp": int(tcp),
        "udp": int(udp),
        "icmp": int(icmp),
    }


snmp_section_palo_alto_sessions = SimpleSNMPSection(
    name="palo_alto_sessions",
    parse_function=parse_palo_alto_sessions,
    fetch=SNMPTree(
        # panSessionUtilization (.1), panSessionMax (.2), panSessionActive (.3),
        # panSessionActiveTcp (.4), panSessionActiveUdp (.5), panSessionActiveICMP (.6)
        base=".1.3.6.1.4.1.25461.2.1.2.3",
        oids=["1", "2", "3", "4", "5", "6"],
    ),
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", "Palo Alto"),
        exists(".1.3.6.1.4.1.25461.2.1.2.3.3.0"),
    ),
)


def discover_palo_alto_sessions(section):
    yield Service()


def check_palo_alto_sessions(params, section):
    yield from check_levels(
        value=section["utilization"],
        levels_upper=params["levels_utilization"],
        metric_name="palo_alto_sessions_utilization",
        render_func=render.percent,
        boundaries=(0, 100),
        label="Utilization",
    )

    yield from check_levels(
        value=section["active"],
        levels_upper=params["levels_active"],
        metric_name="palo_alto_sessions_active",
        render_func=lambda v: f"{v:.0f}",
        boundaries=(0, section["max"]),
        label="Active sessions",
    )
    yield Result(state=State.OK, notice=f"Maximum supported sessions: {section['max']}")

    for proto, metric_name in (
        ("tcp", "palo_alto_sessions_tcp"),
        ("udp", "palo_alto_sessions_udp"),
        ("icmp", "palo_alto_sessions_icmp"),
    ):
        yield Metric(metric_name, section[proto])


check_plugin_palo_alto_sessions = CheckPlugin(
    name="palo_alto_sessions",
    service_name="Palo Alto Sessions",
    discovery_function=discover_palo_alto_sessions,
    check_function=check_palo_alto_sessions,
    check_ruleset_name="palo_alto_sessions_kr",
    check_default_parameters={
        "levels_utilization": ("fixed", (80.0, 90.0)),
        "levels_active": ("no_levels", None),
    },
)
