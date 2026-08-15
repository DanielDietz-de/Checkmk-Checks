from __future__ import annotations

import importlib.util
import json
import sys
import time
import types
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any


class State(IntEnum):
    """Represent state behavior and associated state."""
    OK = 0
    WARN = 1
    CRIT = 2
    UNKNOWN = 3

    @classmethod
    def worst(cls, *states: "State") -> "State":
        """Handle worst for this module's workflow."""
        ranking = {cls.OK: 0, cls.WARN: 1, cls.UNKNOWN: 2, cls.CRIT: 3}
        return max(states, key=ranking.__getitem__)


@dataclass
class Result:
    """Represent result behavior and associated state."""
    state: State
    summary: str | None = None
    details: str | None = None


@dataclass
class Service:
    """Represent service behavior and associated state."""
    item: str


@dataclass
class Metric:
    """Represent metric behavior and associated state."""
    name: str
    value: float
    levels: tuple[float, float] | None = None


class AgentSection:
    """Represent agentsection behavior and associated state."""
    def __init__(self, **kwargs: Any) -> None:
        """Initialize the instance and its required state."""
        self.kwargs = kwargs


class CheckPlugin:
    """Represent checkplugin behavior and associated state."""
    def __init__(self, **kwargs: Any) -> None:
        """Initialize the instance and its required state."""
        self.kwargs = kwargs


v2 = types.ModuleType("cmk.agent_based.v2")
v2.AgentSection = AgentSection
v2.CheckPlugin = CheckPlugin
v2.CheckResult = list
v2.DiscoveryResult = list
v2.Metric = Metric
v2.Result = Result
v2.Service = Service
v2.State = State
v2.StringTable = list[list[str]]

cmk = types.ModuleType("cmk")
agent_based = types.ModuleType("cmk.agent_based")
sys.modules.setdefault("cmk", cmk)
sys.modules.setdefault("cmk.agent_based", agent_based)
sys.modules["cmk.agent_based.v2"] = v2

PLUGIN = Path(__file__).parents[1] / "src/oxidized_backup/agent_based/oxidized_backup.py"
spec = importlib.util.spec_from_file_location("oxidized_backup_check", PLUGIN)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def device(**overrides: Any) -> dict[str, Any]:
    """Handle device for this module's workflow."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "schema_version": 1,
        "kind": "device",
        "host_name": "switch-1",
        "policy": {
            "collection_warning_age_seconds": 3600,
            "collection_critical_age_seconds": 7200,
        },
        "oxidized": {
            "present": True,
            "status": "success",
            "source": "hook",
            "last_attempt_at": now - 60,
            "last_success_at": now - 60,
            "persistent_state": True,
        },
        "git": {
            "exists": True,
            "size": 1234,
            "oid": "a" * 40,
            "repository_id": "default",
            "path": "switch-1",
            "repository_head": "b" * 40,
        },
        "remote": {"status": "synced", "state_hint": 0},
    }
    payload.update(overrides)
    return payload


def central(**overrides: Any) -> dict[str, Any]:
    """Handle central for this module's workflow."""
    payload: dict[str, Any] = {
        "schema_version": 1,
        "kind": "central",
        "policy": {"orphan_state": 1},
        "inventory": {
            "expected": 1,
            "loaded": 1,
            "matched": 1,
            "missing": [],
            "orphans": [],
            "duplicate_oxidized_names": [],
            "errors": [],
            "oxidized_errors": [],
            "hook_state_available": True,
        },
        "repositories": [
            {
                "id": "default",
                "valid": True,
                "head": "a" * 40,
                "expected_files": 1,
                "missing_files": [],
                "empty_files": [],
                "fsck": {"status": "ok"},
                "remote": {
                    "status": "synced",
                    "state_hint": 0,
                    "branch": "main",
                    "local_head": "a" * 40,
                    "remote_head": "a" * 40,
                },
            }
        ],
    }
    payload.update(overrides)
    return payload


def results(item: str, section: dict[str, Any]) -> list[Result | Metric]:
    """Handle results for this module's workflow."""
    return list(module.check_oxidized_backup(item, section))


def result_states(item: str, section: dict[str, Any]) -> list[State]:
    """Handle result states for this module's workflow."""
    return [entry.state for entry in results(item, section) if isinstance(entry, Result)]


def test_parser_and_discovery() -> None:
    """Verify that parser and discovery."""
    payload = device()
    assert module.parse_oxidized_backup([[json.dumps(payload)]]) == payload
    assert [service.item for service in module.discover_oxidized_backup(payload)] == ["backup"]
    assert [service.item for service in module.discover_oxidized_backup(central())] == [
        "backup inventory",
        "Git repository",
        "Git remote synchronization",
    ]


def test_fresh_success_and_git_blob_are_ok() -> None:
    """Verify that fresh success and git blob are ok."""
    states = result_states("backup", device())
    assert states == [State.OK, State.OK]


def test_collection_age_warning_and_critical() -> None:
    """Verify that collection age warning and critical."""
    now = int(time.time())
    warning_payload = device(
        oxidized={
            "present": True,
            "status": "success",
            "last_attempt_at": now - 4000,
            "last_success_at": now - 4000,
            "persistent_state": True,
        }
    )
    assert State.WARN in result_states("backup", warning_payload)
    critical_payload = device(
        oxidized={
            "present": True,
            "status": "success",
            "last_attempt_at": now - 8000,
            "last_success_at": now - 8000,
            "persistent_state": True,
        }
    )
    assert State.CRIT in result_states("backup", critical_payload)


def test_missing_from_oxidized_is_critical() -> None:
    """Verify that missing from oxidized is critical."""
    payload = device(
        oxidized={
            "present": False,
            "status": "missing",
            "last_attempt_at": None,
            "last_success_at": None,
        }
    )
    assert State.CRIT in result_states("backup", payload)


def test_failed_and_never_collection_are_critical() -> None:
    """Verify that failed and never collection are critical."""
    for status in ("never", "no_connection", "timelimit", "fail"):
        payload = device(
            oxidized={
                "present": True,
                "status": status,
                "last_attempt_at": None,
                "last_success_at": None,
            }
        )
        assert State.CRIT in result_states("backup", payload)


def test_missing_or_empty_git_artifact_is_critical() -> None:
    """Verify that missing or empty git artifact is critical."""
    missing = device(git={"exists": False, "repository_id": "default", "path": "switch-1"})
    assert State.CRIT in result_states("backup", missing)
    empty = device(git={"exists": True, "size": 0, "repository_id": "default", "path": "switch-1"})
    assert State.CRIT in result_states("backup", empty)


def test_remote_failure_does_not_multiply_device_alerts() -> None:
    """Verify that remote failure does not multiply device alerts."""
    payload = device(remote={"status": "mismatch", "state_hint": 2})
    assert result_states("backup", payload) == [State.OK, State.OK]


def test_inventory_missing_node_is_critical() -> None:
    """Verify that inventory missing node is critical."""
    payload = central()
    payload["inventory"] = {
        **payload["inventory"],
        "expected": 2,
        "matched": 1,
        "missing": ["switch-2"],
    }
    assert State.CRIT in result_states("backup inventory", payload)


def test_inventory_orphan_uses_configured_state_and_hook_missing_warns() -> None:
    """Verify that inventory orphan uses configured state and hook missing warns."""
    payload = central()
    payload["inventory"] = {
        **payload["inventory"],
        "orphans": ["old-switch"],
        "hook_state_available": False,
    }
    states = result_states("backup inventory", payload)
    assert states == [State.WARN, State.WARN]


def test_repository_missing_file_and_fsck_failure_are_critical() -> None:
    """Verify that repository missing file and fsck failure are critical."""
    payload = central()
    payload["repositories"][0]["missing_files"] = ["switch-1"]
    assert result_states("Git repository", payload) == [State.CRIT]
    payload = central()
    payload["repositories"][0]["fsck"] = {"status": "failed"}
    assert result_states("Git repository", payload) == [State.CRIT]


def test_remote_sync_states() -> None:
    """Verify that remote sync states."""
    assert result_states("Git remote synchronization", central()) == [State.OK]
    payload = central()
    payload["repositories"][0]["remote"] = {
        "status": "mismatch",
        "state_hint": 1,
        "local_head": "a" * 40,
        "remote_head": "b" * 40,
    }
    assert result_states("Git remote synchronization", payload) == [State.WARN]
    payload["repositories"][0]["remote"]["state_hint"] = 2
    assert result_states("Git remote synchronization", payload) == [State.CRIT]


def test_api_error_is_unknown() -> None:
    """Verify that api error is unknown."""
    payload = device(api_error="connection refused")
    assert result_states("backup", payload) == [State.UNKNOWN, State.OK]
