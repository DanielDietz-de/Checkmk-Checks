from __future__ import annotations

import importlib.util
import json
import sys
import types
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any


class State(IntEnum):
    OK = 0
    WARN = 1
    CRIT = 2
    UNKNOWN = 3


@dataclass
class Result:
    state: State
    summary: str | None = None
    details: str | None = None


@dataclass
class Service:
    item: str


class AgentSection:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class CheckPlugin:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


v2 = types.ModuleType("cmk.agent_based.v2")
v2.AgentSection = AgentSection
v2.CheckPlugin = CheckPlugin
v2.CheckResult = list
v2.DiscoveryResult = list
v2.Result = Result
v2.Service = Service
v2.State = State
v2.StringTable = list[list[str]]

cmk = types.ModuleType("cmk")
agent_based = types.ModuleType("cmk.agent_based")
sys.modules.setdefault("cmk", cmk)
sys.modules.setdefault("cmk.agent_based", agent_based)
sys.modules["cmk.agent_based.v2"] = v2

PLUGIN = Path(__file__).parents[1] / "src/switch_port_sync/agent_based/switch_port_sync.py"
spec = importlib.util.spec_from_file_location("switch_port_sync_check", PLUGIN)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def record(item: str, state_a: str, state_b: str) -> dict[str, Any]:
    return {
        "item": item,
        "host_a": {
            "name": "041-Transit-001",
            "state": state_a,
            "reason": "test",
        },
        "host_b": {
            "name": "041-Transit-002",
            "state": state_b,
            "reason": "test",
        },
    }


def section(*records: dict[str, Any]) -> dict[str, Any]:
    return {
        "pair_name": "Transit pair",
        "host_a": "041-Transit-001",
        "host_b": "041-Transit-002",
        "records": list(records),
    }


def result_for(state_a: str, state_b: str) -> Result:
    data = section(record("01", state_a, state_b))
    return list(module.check_switch_port_sync("01", data))[0]


def test_parser() -> None:
    payload = section(record("01", "up", "up"))
    parsed = module.parse_switch_port_sync([[json.dumps(payload)]])
    assert parsed == payload


def test_discovery_baseline() -> None:
    data = section(
        record("up-up", "up", "up"),
        record("up-down", "up", "down"),
        record("down-up", "down", "up"),
        record("up-missing", "up", "missing"),
        record("down-down", "down", "down"),
    )
    assert [service.item for service in module.discover_switch_port_sync(data)] == [
        "Pair status",
        "up-up",
        "up-down",
        "down-up",
        "up-missing",
    ]


def test_requested_state_matrix() -> None:
    assert result_for("up", "up").state == State.OK
    assert result_for("up", "down").state == State.CRIT
    assert result_for("down", "up").state == State.CRIT
    # This service represents a pair accepted when at least one member was up.
    assert result_for("down", "down").state == State.CRIT


def test_missing_stale_unknown_are_unknown() -> None:
    for unresolved in ("missing", "stale", "unknown"):
        assert result_for(unresolved, "up").state == State.UNKNOWN
        assert result_for("up", unresolved).state == State.UNKNOWN


def test_pair_status_reports_query_health_not_port_health() -> None:
    result = list(
        module.check_switch_port_sync(
            "Pair status",
            section(record("01", "down", "down")),
        )
    )[0]
    assert result.state == State.OK
    assert "1 mapped" in (result.summary or "")


def test_pair_status_without_records_is_unknown() -> None:
    result = list(module.check_switch_port_sync("Pair status", section()))[0]
    assert result.state == State.UNKNOWN


def test_pair_status_error_is_unknown() -> None:
    result = list(
        module.check_switch_port_sync(
            "Pair status",
            {"pair_name": "Transit pair", "records": [], "error": "socket unavailable"},
        )
    )[0]
    assert result.state == State.UNKNOWN
