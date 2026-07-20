#!/usr/bin/env python3

"""Unit tests for the additive AudioCodes SBC monitoring plug-ins.

The tests use a minimal Checkmk API stub so parser and alarm-correlation logic can
run on a normal Python interpreter. A separate GitHub Actions job loads the same
files against the real Checkmk 2.4 API.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import pytest


PLUGIN_DIR = Path(__file__).parents[1] / "src" / "acgateway" / "agent_based"


class State(IntEnum):
    OK = 0
    WARN = 1
    CRIT = 2
    UNKNOWN = 3


@dataclass
class Result:
    state: State
    summary: str | None = None
    notice: str | None = None


@dataclass
class Metric:
    name: str
    value: float
    boundaries: tuple[float | None, float | None] | None = None


class Service:
    pass


class OIDEnd:
    pass


class GetRateError(Exception):
    pass


class _Definition:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _contains(*args):
    return args


def _install_checkmk_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    cmk = types.ModuleType("cmk")
    agent_based = types.ModuleType("cmk.agent_based")
    v2 = types.ModuleType("cmk.agent_based.v2")

    for name, value in {
        "CheckPlugin": _Definition,
        "SNMPSection": _Definition,
        "SNMPTree": _Definition,
        "Metric": Metric,
        "Result": Result,
        "Service": Service,
        "OIDEnd": OIDEnd,
        "State": State,
        "GetRateError": GetRateError,
        "contains": _contains,
        "get_rate": lambda *_args, **_kwargs: 0.0,
        "get_value_store": dict,
    }.items():
        setattr(v2, name, value)

    monkeypatch.setitem(sys.modules, "cmk", cmk)
    monkeypatch.setitem(sys.modules, "cmk.agent_based", agent_based)
    monkeypatch.setitem(sys.modules, "cmk.agent_based.v2", v2)


def _load_plugin(monkeypatch: pytest.MonkeyPatch, name: str):
    _install_checkmk_stub(monkeypatch)
    module_name = f"test_acgateway_{name}"
    spec = importlib.util.spec_from_file_location(module_name, PLUGIN_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_call_capacity_parses_current_and_retained_peaks(monkeypatch):
    plugin = _load_plugin(monkeypatch, "call_capacity")

    section = plugin.parse_acgateway_call_capacity(
        [
            [["10", "11", "9"]],
            [
                ["107", "8", "9", "7"],
                ["108", "12", "14", "13"],
                ["109", "null", "11", "10"],
            ],
        ]
    )

    assert section == {
        "active_calls_in": 10,
        "active_calls_out": 11,
        "active_sessions": 9,
        "active_calls_in_max": 12,
        "active_calls_out_max": 14,
        "active_sessions_max": 13,
    }


def test_call_capacity_does_not_treat_null_as_zero(monkeypatch):
    plugin = _load_plugin(monkeypatch, "call_capacity")
    assert plugin.parse_acgateway_call_capacity(
        [[["null", "null", "null"]], [["110", "null", "null", "null"]]]
    ) is None


def test_license_headroom_uses_the_more_constrained_license(monkeypatch):
    plugin = _load_plugin(monkeypatch, "license")

    section = plugin.parse_acgateway_license(
        [
            [["35.5", "42"]],
            [["107", "55", "48"], ["108", "51", "63"]],
        ]
    )

    assert section == {
        "media_usage": 35.5,
        "signaling_usage": 42.0,
        "media_usage_max": 55.0,
        "signaling_usage_max": 63.0,
        "idle_capacity": 58.0,
        "idle_capacity_min": 37.0,
    }


def test_ha_parses_fractional_percent_units_and_module_states(monkeypatch):
    plugin = _load_plugin(monkeypatch, "ha")

    section = plugin.parse_acgateway_ha(
        [
            [["125", "250"]],
            [["107", "80", "110"], ["108", "175", "320"]],
            [["1", "2", "1", "2"], ["2", "2", "1", "3"]],
        ]
    )

    assert section["redundant_packet_loss"] == 1.25
    assert section["active_packet_loss"] == 2.5
    assert section["redundant_packet_loss_max"] == 1.75
    assert section["active_packet_loss_max"] == 3.2
    assert section["modules"] == [
        {"index": "1", "operational_state": "2", "presence": "1", "ha_status": "2"},
        {"index": "2", "operational_state": "2", "presence": "1", "ha_status": "3"},
    ]


def test_ha_alarm_filter_finds_mismatch_and_sync_faults(monkeypatch):
    plugin = _load_plugin(monkeypatch, "ha")
    alarms = {
        "alarms": [
            {"name": "acHASystemConfigMismatchAlarm", "desc": "Configuration differs"},
            {"name": "OtherAlarm", "desc": "Redundant unit not synchronized"},
            {"name": "Unrelated", "desc": "Fan warning"},
        ]
    }

    assert [alarm["name"] for alarm in plugin._ha_alarms(alarms)] == [
        "acHASystemConfigMismatchAlarm",
        "OtherAlarm",
    ]


def test_tls_parses_current_counters_and_25_hour_peaks(monkeypatch):
    plugin = _load_plugin(monkeypatch, "tls")

    section = plugin.parse_acgateway_tls(
        [
            [["1000", "20", "17"]],
            [
                ["107", "10", "15", "2", "120"],
                ["108", "11", "22", "4", "180"],
            ],
        ]
    )

    assert section == {
        "attempted_total": 1000,
        "rejected_total": 20,
        "active_connections": 17,
        "active_connections_max": 22,
        "rejected_connections_max": 4,
        "attempted_connections_max": 180,
    }


def test_tls_alarm_filter_finds_certificate_and_socket_limit_alarms(monkeypatch):
    plugin = _load_plugin(monkeypatch, "tls")
    alarms = {
        "alarms": [
            {"name": "acCertificateExpiryAlarm", "desc": "Certificate expires soon"},
            {"name": "acTLSSocketsLimitAlarm", "desc": "TLS sockets threshold reached"},
            {"name": "Unrelated", "desc": "Interface down"},
        ]
    }

    assert [alarm["name"] for alarm in plugin._tls_alarms(alarms)] == [
        "acCertificateExpiryAlarm",
        "acTLSSocketsLimitAlarm",
    ]
