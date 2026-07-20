#!/usr/bin/env python3

"""Graphing definitions for the extended AudioCodes SBC checks."""

from cmk.graphing.v1.graphs import Graph, Title
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, StrictPrecision, Unit


_COUNT = Unit(DecimalNotation(""), StrictPrecision(1))
_PERCENT = Unit(DecimalNotation("%"), StrictPrecision(1))
_RATE = Unit(DecimalNotation("1/s"), StrictPrecision(3))


metric_active_calls_in = Metric(
    name="active_calls_in",
    title=Title("Active Calls In"),
    unit=_COUNT,
    color=Color.BLUE,
)
metric_active_calls_out = Metric(
    name="active_calls_out",
    title=Title("Active Calls Out"),
    unit=_COUNT,
    color=Color.GREEN,
)
metric_active_sessions = Metric(
    name="active_sessions",
    title=Title("Active Sessions"),
    unit=_COUNT,
    color=Color.ORANGE,
)
metric_active_calls_in_max = Metric(
    name="active_calls_in_max",
    title=Title("Active Calls In Max"),
    unit=_COUNT,
    color=Color.BLUE,
)
metric_active_calls_out_max = Metric(
    name="active_calls_out_max",
    title=Title("Active Calls Out Max"),
    unit=_COUNT,
    color=Color.GREEN,
)
metric_active_sessions_max = Metric(
    name="active_sessions_max",
    title=Title("Active Sessions Max"),
    unit=_COUNT,
    color=Color.ORANGE,
)

metric_sbc_media_license_usage = Metric(
    name="sbc_media_license_usage",
    title=Title("SBC Media License Usage"),
    unit=_PERCENT,
    color=Color.BLUE,
)
metric_sbc_signaling_license_usage = Metric(
    name="sbc_signaling_license_usage",
    title=Title("SBC Signaling License Usage"),
    unit=_PERCENT,
    color=Color.GREEN,
)
metric_sbc_media_license_usage_max = Metric(
    name="sbc_media_license_usage_max",
    title=Title("SBC Media License Usage Max"),
    unit=_PERCENT,
    color=Color.BLUE,
)
metric_sbc_signaling_license_usage_max = Metric(
    name="sbc_signaling_license_usage_max",
    title=Title("SBC Signaling License Usage Max"),
    unit=_PERCENT,
    color=Color.GREEN,
)
metric_sbc_license_idle_capacity = Metric(
    name="sbc_license_idle_capacity",
    title=Title("SBC Idle Licensed Capacity"),
    unit=_PERCENT,
    color=Color.ORANGE,
)
metric_sbc_license_idle_capacity_min = Metric(
    name="sbc_license_idle_capacity_min",
    title=Title("SBC Minimum Idle Licensed Capacity"),
    unit=_PERCENT,
    color=Color.RED,
)

metric_ha_active_packet_loss = Metric(
    name="ha_active_packet_loss",
    title=Title("HA Active-Unit Packet Loss"),
    unit=_PERCENT,
    color=Color.BLUE,
)
metric_ha_redundant_packet_loss = Metric(
    name="ha_redundant_packet_loss",
    title=Title("HA Redundant-Unit Packet Loss"),
    unit=_PERCENT,
    color=Color.GREEN,
)
metric_ha_active_packet_loss_max = Metric(
    name="ha_active_packet_loss_max",
    title=Title("HA Active-Unit Packet Loss Max"),
    unit=_PERCENT,
    color=Color.BLUE,
)
metric_ha_redundant_packet_loss_max = Metric(
    name="ha_redundant_packet_loss_max",
    title=Title("HA Redundant-Unit Packet Loss Max"),
    unit=_PERCENT,
    color=Color.GREEN,
)

metric_active_tls_connections = Metric(
    name="active_tls_connections",
    title=Title("Active SIP TLS Connections"),
    unit=_COUNT,
    color=Color.BLUE,
)
metric_active_tls_connections_max = Metric(
    name="active_tls_connections_max",
    title=Title("Active SIP TLS Connections Max"),
    unit=_COUNT,
    color=Color.GREEN,
)
metric_attempted_tls_connections_max = Metric(
    name="attempted_tls_connections_max",
    title=Title("Attempted SIP TLS Connections per Interval"),
    unit=_COUNT,
    color=Color.ORANGE,
)
metric_rejected_tls_connections_max = Metric(
    name="rejected_tls_connections_max",
    title=Title("Rejected SIP TLS Connections per Interval"),
    unit=_COUNT,
    color=Color.RED,
)
metric_tls_connection_attempts_per_sec = Metric(
    name="tls_connection_attempts_per_sec",
    title=Title("SIP TLS Connection Attempts"),
    unit=_RATE,
    color=Color.BLUE,
)
metric_tls_rejected_connections_per_sec = Metric(
    name="tls_rejected_connections_per_sec",
    title=Title("Rejected SIP TLS Connections"),
    unit=_RATE,
    color=Color.RED,
)


graph_acgateway_call_capacity_current = Graph(
    name="acgateway_call_capacity_current",
    title=Title("SBC Current Call Capacity"),
    simple_lines=["active_calls_in", "active_calls_out", "active_sessions"],
)
graph_acgateway_call_capacity_peaks = Graph(
    name="acgateway_call_capacity_peaks",
    title=Title("SBC Retained Call Peaks"),
    simple_lines=["active_calls_in_max", "active_calls_out_max", "active_sessions_max"],
)
graph_acgateway_license_usage = Graph(
    name="acgateway_license_usage",
    title=Title("SBC License Usage"),
    simple_lines=[
        "sbc_media_license_usage",
        "sbc_signaling_license_usage",
        "sbc_license_idle_capacity",
    ],
)
graph_acgateway_ha_packet_loss = Graph(
    name="acgateway_ha_packet_loss",
    title=Title("SBC HA Keepalive Packet Loss"),
    simple_lines=[
        "ha_active_packet_loss",
        "ha_redundant_packet_loss",
        "ha_active_packet_loss_max",
        "ha_redundant_packet_loss_max",
    ],
)
graph_acgateway_tls_connections = Graph(
    name="acgateway_tls_connections",
    title=Title("SIP TLS Connections"),
    simple_lines=["active_tls_connections", "active_tls_connections_max"],
)
