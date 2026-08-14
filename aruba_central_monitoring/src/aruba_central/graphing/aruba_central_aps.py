"""Graphing API V1 metric and graph definitions for Aruba Central monitoring."""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, Unit
from cmk.graphing.v1.perfometers import Closed, FocusRange, Perfometer

metric_aruba_api_rate_remaining = Metric(name="aruba_api_rate_remaining", title=Title("Aruba API calls remaining"), unit=Unit(DecimalNotation("calls")), color=Color.ORANGE)
metric_aruba_api_rate_limit = Metric(name="aruba_api_rate_limit", title=Title("Aruba API call limit"), unit=Unit(DecimalNotation("calls")), color=Color.BLUE)
metric_aruba_last_success_age_seconds = Metric(name="aruba_last_success_age_seconds", title=Title("Last successful collection age"), unit=Unit(DecimalNotation("s")), color=Color.PINK)
metric_aruba_refresh_duration_seconds = Metric(name="aruba_refresh_duration_seconds", title=Title("cencli duration"), unit=Unit(DecimalNotation("s")), color=Color.BLUE)
metric_aruba_ap_total = Metric(name="aruba_ap_total", title=Title("APs total"), unit=Unit(DecimalNotation("APs")), color=Color.BLUE)
metric_aruba_ap_up = Metric(name="aruba_ap_up", title=Title("APs Up"), unit=Unit(DecimalNotation("APs")), color=Color.PINK)
metric_aruba_ap_down = Metric(name="aruba_ap_down", title=Title("APs not Up"), unit=Unit(DecimalNotation("APs")), color=Color.ORANGE)
metric_aruba_ap_down_checked = Metric(name="aruba_ap_down_checked", title=Title("APs not Up checked"), unit=Unit(DecimalNotation("APs")), color=Color.ORANGE)
metric_aruba_clients_total = Metric(name="aruba_clients_total", title=Title("Wireless clients total"), unit=Unit(DecimalNotation("clients")), color=Color.BLUE)
metric_aruba_ap_cpu_percent = Metric(name="aruba_ap_cpu_percent", title=Title("AP CPU utilization"), unit=Unit(DecimalNotation("%")), color=Color.ORANGE)
metric_aruba_ap_mem_free_percent = Metric(name="aruba_ap_mem_free_percent", title=Title("AP free memory"), unit=Unit(DecimalNotation("%")), color=Color.BLUE)
metric_aruba_ap_clients = Metric(name="aruba_ap_clients", title=Title("AP clients"), unit=Unit(DecimalNotation("clients")), color=Color.PINK)
metric_aruba_ap_mem_total_mb = Metric(name="aruba_ap_mem_total_mb", title=Title("AP memory total"), unit=Unit(DecimalNotation("MB")), color=Color.BLUE)
metric_aruba_ap_mem_free_mb = Metric(name="aruba_ap_mem_free_mb", title=Title("AP memory free"), unit=Unit(DecimalNotation("MB")), color=Color.PINK)
metric_aruba_ap_uptime_seconds = Metric(name="aruba_ap_uptime_seconds", title=Title("AP uptime"), unit=Unit(DecimalNotation("s")), color=Color.BLUE)
metric_aruba_ap_ssid_count = Metric(name="aruba_ap_ssid_count", title=Title("AP SSIDs"), unit=Unit(DecimalNotation("SSIDs")), color=Color.PINK)
metric_aruba_radio_utilization_percent = Metric(name="aruba_radio_utilization_percent", title=Title("Radio utilization"), unit=Unit(DecimalNotation("%")), color=Color.ORANGE)
metric_aruba_radio_tx_power_dbm = Metric(name="aruba_radio_tx_power_dbm", title=Title("Radio TX power"), unit=Unit(DecimalNotation("dBm")), color=Color.PINK)

graph_aruba_central_summary_aps = Graph(name="aruba_central_summary_aps", title=Title("Aruba Central AP overview"), simple_lines=["aruba_ap_total", "aruba_ap_up", "aruba_ap_down"], minimal_range=MinimalRange(0, 10))
graph_aruba_central_summary_api = Graph(name="aruba_central_summary_api", title=Title("Aruba Central API rate limit"), simple_lines=["aruba_api_rate_remaining", "aruba_api_rate_limit"], minimal_range=MinimalRange(0, 100))
graph_aruba_central_collector = Graph(name="aruba_central_collector", title=Title("Aruba Central collection"), simple_lines=["aruba_last_success_age_seconds", "aruba_refresh_duration_seconds"], minimal_range=MinimalRange(0, 60))
graph_aruba_central_ap_resources = Graph(name="aruba_central_ap_resources", title=Title("AP resources"), simple_lines=["aruba_ap_cpu_percent", "aruba_ap_mem_free_percent"], minimal_range=MinimalRange(0, 100))
graph_aruba_central_ap_clients = Graph(name="aruba_central_ap_clients", title=Title("AP clients"), simple_lines=["aruba_ap_clients"], minimal_range=MinimalRange(0, 10))
graph_aruba_central_radio = Graph(name="aruba_central_radio", title=Title("Radio utilization and TX power"), simple_lines=["aruba_radio_utilization_percent", "aruba_radio_tx_power_dbm"], minimal_range=MinimalRange(0, 100))

perfometer_aruba_central_summary = Perfometer(name="aruba_central_summary", focus_range=FocusRange(Closed(0), Closed(100)), segments=["aruba_api_rate_remaining"])
perfometer_aruba_central_ap = Perfometer(name="aruba_central_ap", focus_range=FocusRange(Closed(0), Closed(100)), segments=["aruba_ap_cpu_percent"])
perfometer_aruba_central_radio = Perfometer(name="aruba_central_radio", focus_range=FocusRange(Closed(0), Closed(100)), segments=["aruba_radio_utilization_percent"])
