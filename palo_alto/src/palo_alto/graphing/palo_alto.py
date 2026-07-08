#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import (
    Color,
    DecimalNotation,
    Metric,
    StrictPrecision,
    Unit,
)

UNIT_PER_SECOND = Unit(DecimalNotation("/s"), StrictPrecision(2))
UNIT_COUNT = Unit(DecimalNotation(""), StrictPrecision(0))
UNIT_PERCENT = Unit(DecimalNotation("%"), StrictPrecision(1))


metric_palo_alto_dos_zone_red_activate = Metric(
    name="palo_alto_dos_zone_red_activate",
    title=Title("DoS Zone RED activate drops"),
    unit=UNIT_PER_SECOND,
    color=Color.ORANGE,
)
metric_palo_alto_dos_zone_red_maximum = Metric(
    name="palo_alto_dos_zone_red_maximum",
    title=Title("DoS Zone RED maximum drops"),
    unit=UNIT_PER_SECOND,
    color=Color.RED,
)

graph_palo_alto_dos_zone_red = Graph(
    name="palo_alto_dos_zone_red",
    title=Title("DoS Zone RED Drops"),
    simple_lines=[
        "palo_alto_dos_zone_red_activate",
        "palo_alto_dos_zone_red_maximum",
    ],
)


metric_palo_alto_sessions_utilization = Metric(
    name="palo_alto_sessions_utilization",
    title=Title("Session table utilization"),
    unit=UNIT_PERCENT,
    color=Color.PURPLE,
)
metric_palo_alto_sessions_active = Metric(
    name="palo_alto_sessions_active",
    title=Title("Active sessions"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)
metric_palo_alto_sessions_tcp = Metric(
    name="palo_alto_sessions_tcp",
    title=Title("Active TCP sessions"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)
metric_palo_alto_sessions_udp = Metric(
    name="palo_alto_sessions_udp",
    title=Title("Active UDP sessions"),
    unit=UNIT_COUNT,
    color=Color.YELLOW,
)
metric_palo_alto_sessions_icmp = Metric(
    name="palo_alto_sessions_icmp",
    title=Title("Active ICMP sessions"),
    unit=UNIT_COUNT,
    color=Color.CYAN,
)

graph_palo_alto_sessions = Graph(
    name="palo_alto_sessions_by_protocol",
    title=Title("Palo Alto active sessions by protocol"),
    simple_lines=[
        "palo_alto_sessions_tcp",
        "palo_alto_sessions_udp",
        "palo_alto_sessions_icmp",
    ],
    compound_lines=["palo_alto_sessions_active"],
)
