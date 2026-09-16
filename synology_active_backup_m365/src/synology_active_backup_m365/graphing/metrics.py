#!/usr/bin/env python3
"""Graphing definitions for Synology Active Backup for Microsoft 365 metrics."""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, Unit

metric_synology_m365_collector_age = Metric(
    name="synology_m365_collector_age",
    title=Title("Synology M365 collector age"),
    unit=Unit(DecimalNotation("s")),
    color=Color.BLUE,
)
metric_synology_m365_last_success_age = Metric(
    name="synology_m365_last_success_age",
    title=Title("Last successful M365 backup age"),
    unit=Unit(DecimalNotation("s")),
    color=Color.ORANGE,
)
metric_synology_m365_backup_age = Metric(
    name="synology_m365_backup_age",
    title=Title("Latest M365 backup run age"),
    unit=Unit(DecimalNotation("s")),
    color=Color.PINK,
)
metric_synology_m365_runtime = Metric(
    name="synology_m365_runtime",
    title=Title("M365 backup runtime"),
    unit=Unit(DecimalNotation("s")),
    color=Color.BLUE,
)
metric_synology_m365_transferred_size = Metric(
    name="synology_m365_transferred_size",
    title=Title("M365 transferred data"),
    unit=Unit(DecimalNotation("B")),
    color=Color.PINK,
)

graph_synology_m365_backup_ages = Graph(
    name="synology_m365_backup_ages",
    title=Title("Microsoft 365 backup ages"),
    simple_lines=["synology_m365_last_success_age", "synology_m365_backup_age"],
    minimal_range=MinimalRange(0, 3600),
)
graph_synology_m365_runtime = Graph(
    name="synology_m365_runtime",
    title=Title("Microsoft 365 backup runtime"),
    simple_lines=["synology_m365_runtime"],
    minimal_range=MinimalRange(0, 60),
)
graph_synology_m365_transfer = Graph(
    name="synology_m365_transfer",
    title=Title("Microsoft 365 transferred data"),
    simple_lines=["synology_m365_transferred_size"],
    minimal_range=MinimalRange(0, 1),
)
