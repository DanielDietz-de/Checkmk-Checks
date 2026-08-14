"""Focused parser and state tests for the Aruba Central Check API plug-in."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import types

PACKAGE = Path(__file__).resolve().parents[1]
PLUGIN = PACKAGE / "src/aruba_central/agent_based/aruba_central_aps.py"


class _State:
    OK = "OK"
    WARN = "WARN"
    CRIT = "CRIT"
    UNKNOWN = "UNKNOWN"


class _Result:
    def __init__(self, state, summary, details=None):
        self.state = state
        self.summary = summary
        self.details = details


class _Metric:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class _Service:
    def __init__(self, item=None):
        self.item = item


def _check_levels(value, **kwargs):
    yield _Metric(kwargs["metric_name"], value)


def _load(monkeypatch):
    api = types.ModuleType("cmk.agent_based.v2")
    api.AgentSection = lambda **kwargs: kwargs
    api.CheckPlugin = lambda **kwargs: kwargs
    api.Metric = _Metric
    api.Result = _Result
    api.Service = _Service
    api.State = _State
    api.check_levels = _check_levels
    monkeypatch.setitem(sys.modules, "cmk", types.ModuleType("cmk"))
    monkeypatch.setitem(sys.modules, "cmk.agent_based", types.ModuleType("cmk.agent_based"))
    monkeypatch.setitem(sys.modules, "cmk.agent_based.v2", api)
    spec = importlib.util.spec_from_file_location("aruba_central_aps_test", PLUGIN)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _row(value: dict) -> list[list[str]]:
    return [[json.dumps(value, separators=(",", ":"))]]


def _collector_payload() -> dict:
    return {
        "schema": 1,
        "kind": "collector",
        "collector": {
            "status": "OK",
            "message": "Counts: ap: 2 (1:1), clients: 41",
            "generated_at": "2026-08-06T18:00:00Z",
            "stale": False,
            "last_success_age_seconds": 0,
            "refresh_duration_seconds": 31.25,
            "json_stream": "stdout",
            "counts_stream": "stderr",
            "rate_limit_stream": "stderr",
            "ap_total": 2,
            "ap_up": 1,
            "ap_down": 1,
            "clients_total": 41,
            "api_rate_remaining": 11964,
            "api_rate_limit": 11970,
        },
    }


def _ap_payload() -> dict:
    return {
        "schema": 1,
        "kind": "ap",
        "collector": {
            "generated_at": "2026-08-06T18:00:00Z",
            "stale": False,
            "last_success_age_seconds": 0,
        },
        "ap": {
            "host_name": "AP_CNRPKV30C2",
            "name": "50:e4:e0:cf:5e:68",
            "status": "Up",
            "type": "ap",
            "model": "575",
            "clients": 34,
            "ip": "10.76.8.48/22",
            "mac": "50:e4:e0:cf:5e:68",
            "serial": "CNRPKV30C2",
            "group": "Campus Bornheim",
            "site": "Campus Bornheim - ABS5",
            "uptime": "15w 3d 15m",
            "uptime_seconds": 9288900,
            "cpu_percent": 10.0,
            "mem_total_mb": 920.39,
            "mem_free_mb": 312.2,
            "version": "10.7.1.1_92045",
            "ssid_count": 4,
            "sleep_status": False,
            "radios": [
                {
                    "index": 0,
                    "radio_name": "Radio 5 GHz",
                    "radio_type": "802.11ax",
                    "band": 1,
                    "channel": "157E",
                    "status": "Up",
                    "tx_power": 13,
                    "utilization": 14,
                    "spatial_stream": "4x4:4",
                    "macaddr": "50:e4:e0:75:e6:90",
                }
            ],
        },
    }


def test_collector_parser_and_stream_visibility(monkeypatch):
    plugin = _load(monkeypatch)
    section = plugin.parse_aruba_central_aps(_row(_collector_payload()))
    assert section.kind == "collector"
    assert section.collector.json_stream == "stdout"
    assert section.collector.counts_stream == "stderr"
    assert section.collector.rate_limit_stream == "stderr"
    services = list(plugin.discover_summary(section))
    assert len(services) == 1
    results = list(plugin.check_summary(plugin.check_plugin_aruba_central_summary["check_default_parameters"], section))
    assert any(isinstance(result, _Result) and "1/2 APs Up" in result.summary for result in results)
    assert any(isinstance(result, _Result) and "Counts stream: stderr" in (result.details or "") for result in results)
    assert {result.name for result in results if isinstance(result, _Metric)} >= {
        "aruba_ap_total",
        "aruba_api_rate_remaining",
        "aruba_last_success_age_seconds",
    }


def test_ap_and_radio_services(monkeypatch):
    plugin = _load(monkeypatch)
    section = plugin.parse_aruba_central_aps(_row(_ap_payload()))
    assert section.access_point.host_name == "AP_CNRPKV30C2"
    assert section.access_point.mem_free_mb == 312.2
    assert [service.item for service in plugin.discover_access_point(section)] == [None]
    radio_services = list(plugin.discover_radio(section))
    assert [service.item for service in radio_services] == ["Radio_5_GHz_0"]
    ap_results = list(plugin.check_access_point(plugin.check_plugin_aruba_central_ap["check_default_parameters"], section))
    assert any(isinstance(result, _Result) and result.state == _State.OK for result in ap_results)
    radio_results = list(
        plugin.check_radio(
            "Radio_5_GHz_0",
            plugin.check_plugin_aruba_central_radio["check_default_parameters"],
            section,
        )
    )
    assert any(isinstance(result, _Metric) and result.name == "aruba_radio_utilization_percent" for result in radio_results)


def test_radio_service_keys_preserve_normalized_name_collisions(monkeypatch):
    plugin = _load(monkeypatch)
    payload = _ap_payload()
    payload["ap"]["radios"] = [
        {
            "index": 0,
            "radio_name": "Radio 5 GHz",
            "status": "Up",
        },
        {
            "index": 1,
            "radio_name": "Radio_5_GHz",
            "status": "Up",
        },
    ]
    section = plugin.parse_aruba_central_aps(_row(payload))
    services = list(plugin.discover_radio(section))
    assert [service.item for service in services] == ["Radio_5_GHz_0", "Radio_5_GHz_1"]
    assert len(section.access_point.radios) == 2
    assert section.access_point.radios["Radio_5_GHz_0"].index == 0
    assert section.access_point.radios["Radio_5_GHz_1"].index == 1


def test_radio_service_fallback_key_is_rechecked_until_unique(monkeypatch):
    plugin = _load(monkeypatch)
    payload = _ap_payload()
    payload["ap"]["radios"] = [
        {"index": 0, "radio_name": "A", "status": "Up"},
        {"index": 2, "radio_name": "A_0", "status": "Up"},
        {"index": 0, "radio_name": "A", "status": "Up"},
    ]
    section = plugin.parse_aruba_central_aps(_row(payload))
    services = list(plugin.discover_radio(section))
    assert [service.item for service in services] == ["A_0", "A_0_2", "A_0_3"]
    assert len(section.access_point.radios) == 3
    assert section.access_point.radios["A_0"].index == 0
    assert section.access_point.radios["A_0_2"].index == 2
    assert section.access_point.radios["A_0_3"].index == 0


def test_failed_collector_is_critical(monkeypatch):
    plugin = _load(monkeypatch)
    payload = _collector_payload()
    payload["collector"].update(
        {
            "status": "ERROR",
            "message": "cencli timed out; using last-known-good AP data",
            "stale": True,
            "last_success_age_seconds": 400,
        }
    )
    section = plugin.parse_aruba_central_aps(_row(payload))
    results = list(plugin.check_summary(plugin.check_plugin_aruba_central_summary["check_default_parameters"], section))
    assert any(isinstance(result, _Result) and result.state == _State.CRIT for result in results)


def test_invalid_document_does_not_discover(monkeypatch):
    plugin = _load(monkeypatch)
    section = plugin.parse_aruba_central_aps([["not-json"]])
    assert section.kind == "invalid"
    assert list(plugin.discover_summary(section)) == []
    assert list(plugin.discover_access_point(section)) == []
