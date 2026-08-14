#!/usr/bin/env python3
"""Register Graphing API V1 metrics, graphs, and perfometers for S2D/HCI."""

from __future__ import annotations

from cmk.graphing.v1 import Title, graphs, perfometers
from cmk.graphing.v1.metrics import Color, DecimalNotation, IECNotation, Metric, Unit

metric_s2d_hci_percent_free = Metric(
    name="s2d_hci_percent_free",
    title=Title("S2D/HCI CSV free space"),
    unit=Unit(DecimalNotation("%")),
    color=Color.BLUE,
)
metric_s2d_hci_volume_percent_free = Metric(
    name="s2d_hci_volume_percent_free",
    title=Title("S2D/HCI volume free space"),
    unit=Unit(DecimalNotation("%")),
    color=Color.BLUE,
)
metric_s2d_hci_pool_allocated_bytes = Metric(
    name="s2d_hci_pool_allocated_bytes",
    title=Title("S2D/HCI pool allocated"),
    unit=Unit(IECNotation("B")),
    color=Color.GREEN,
)
metric_s2d_hci_storage_job_percent = Metric(
    name="s2d_hci_storage_job_percent",
    title=Title("S2D/HCI storage job progress"),
    unit=Unit(DecimalNotation("%")),
    color=Color.ORANGE,
)
metric_s2d_hci_virtualization_workload_cpu_usage = Metric(
    name="s2d_hci_virtualization_workload_cpu_usage",
    title=Title("S2D/HCI workload CPU usage"),
    unit=Unit(DecimalNotation("%")),
    color=Color.ORANGE,
)
metric_s2d_hci_virtualization_workload_memory_pressure = Metric(
    name="s2d_hci_virtualization_workload_memory_pressure",
    title=Title("S2D/HCI workload memory pressure"),
    unit=Unit(DecimalNotation("%")),
    color=Color.BLUE,
)
metric_s2d_hci_virtualization_checkpoint_age_hours = Metric(
    name="s2d_hci_virtualization_checkpoint_age_hours",
    title=Title("S2D/HCI checkpoint age"),
    unit=Unit(DecimalNotation("h")),
    color=Color.ORANGE,
)

graph_s2d_hci_csv_free = graphs.Graph(
    name="s2d_hci_csv_free",
    title=Title("S2D/HCI CSV free space"),
    simple_lines=["s2d_hci_percent_free"],
)
graph_s2d_hci_volume_free = graphs.Graph(
    name="s2d_hci_volume_free",
    title=Title("S2D/HCI volume free space"),
    simple_lines=["s2d_hci_volume_percent_free"],
)
graph_s2d_hci_pool_allocated = graphs.Graph(
    name="s2d_hci_pool_allocated",
    title=Title("S2D/HCI pool allocated bytes"),
    simple_lines=["s2d_hci_pool_allocated_bytes"],
)
graph_s2d_hci_storage_job = graphs.Graph(
    name="s2d_hci_storage_job",
    title=Title("S2D/HCI storage job progress"),
    simple_lines=["s2d_hci_storage_job_percent"],
)
graph_s2d_hci_workload_cpu = graphs.Graph(
    name="s2d_hci_workload_cpu",
    title=Title("S2D/HCI workload CPU usage"),
    simple_lines=["s2d_hci_virtualization_workload_cpu_usage"],
)
graph_s2d_hci_workload_memory_pressure = graphs.Graph(
    name="s2d_hci_workload_memory_pressure",
    title=Title("S2D/HCI workload memory pressure"),
    simple_lines=["s2d_hci_virtualization_workload_memory_pressure"],
)
graph_s2d_hci_checkpoint_age = graphs.Graph(
    name="s2d_hci_checkpoint_age",
    title=Title("S2D/HCI checkpoint age"),
    simple_lines=["s2d_hci_virtualization_checkpoint_age_hours"],
)

perfometer_s2d_hci_csv_free = perfometers.Perfometer(
    name="s2d_hci_csv_free",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
    segments=["s2d_hci_percent_free"],
)
perfometer_s2d_hci_volume_free = perfometers.Perfometer(
    name="s2d_hci_volume_free",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
    segments=["s2d_hci_volume_percent_free"],
)
