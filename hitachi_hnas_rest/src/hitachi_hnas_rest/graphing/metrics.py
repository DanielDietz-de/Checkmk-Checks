#!/usr/bin/env python3
"""
Hitachi HNAS Graphing

Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""
from cmk.graphing.v1 import Title, graphs, metrics, perfometers

UNIT_PERCENT = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_COUNT = metrics.Unit(metrics.DecimalNotation(""))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_hnas_fs_used_percent = metrics.Metric(
    name="hnas_fs_used_percent",
    title=Title("Used space"),
    unit=UNIT_PERCENT,
    color=metrics.Color.BLUE,
)

metric_hnas_fs_used = metrics.Metric(
    name="hnas_fs_used",
    title=Title("Used space"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

metric_hnas_fs_size = metrics.Metric(
    name="hnas_fs_size",
    title=Title("Total size"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_BLUE,
)

metric_hnas_fs_snapshot_used = metrics.Metric(
    name="hnas_fs_snapshot_used",
    title=Title("Used by snapshots"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)

metric_hnas_pool_used_percent = metrics.Metric(
    name="hnas_pool_used_percent",
    title=Title("Used space"),
    unit=UNIT_PERCENT,
    color=metrics.Color.BLUE,
)

metric_hnas_pool_used = metrics.Metric(
    name="hnas_pool_used",
    title=Title("Used space"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

metric_hnas_pool_size = metrics.Metric(
    name="hnas_pool_size",
    title=Title("Total size"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_BLUE,
)

metric_hnas_snapshots = metrics.Metric(
    name="hnas_snapshots",
    title=Title("Number of snapshots"),
    unit=UNIT_COUNT,
    color=metrics.Color.PURPLE,
)

metric_hnas_snapshot_age_oldest = metrics.Metric(
    name="hnas_snapshot_age_oldest",
    title=Title("Age of oldest snapshot"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)

metric_hnas_snapshot_age_newest = metrics.Metric(
    name="hnas_snapshot_age_newest",
    title=Title("Time since last snapshot"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)

graph_hnas_fs_usage = graphs.Graph(
    name="hnas_fs_usage",
    title=Title("Filesystem usage"),
    compound_lines=["hnas_fs_used", "hnas_fs_snapshot_used"],
    simple_lines=["hnas_fs_size"],
)

graph_hnas_pool_usage = graphs.Graph(
    name="hnas_pool_usage",
    title=Title("Storage pool usage"),
    compound_lines=["hnas_pool_used"],
    simple_lines=["hnas_pool_size"],
)

graph_hnas_snapshot_age = graphs.Graph(
    name="hnas_snapshot_age",
    title=Title("Snapshot age"),
    simple_lines=["hnas_snapshot_age_oldest", "hnas_snapshot_age_newest"],
)

perfometer_hnas_fs_used_percent = perfometers.Perfometer(
    name="hnas_fs_used_percent",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100),
    ),
    segments=["hnas_fs_used_percent"],
)

perfometer_hnas_pool_used_percent = perfometers.Perfometer(
    name="hnas_pool_used_percent",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100),
    ),
    segments=["hnas_pool_used_percent"],
)
