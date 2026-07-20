from __future__ import annotations

import importlib.util
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest


@dataclass
class HostConfig:
    name: str


@dataclass
class SpecialAgentCommand:
    command_arguments: list[str]


class SpecialAgentConfig:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


def noop_parser(value: object) -> object:
    return value


v1 = types.ModuleType("cmk.server_side_calls.v1")
v1.HostConfig = HostConfig
v1.noop_parser = noop_parser
v1.SpecialAgentCommand = SpecialAgentCommand
v1.SpecialAgentConfig = SpecialAgentConfig

cmk = types.ModuleType("cmk")
server_side_calls = types.ModuleType("cmk.server_side_calls")
sys.modules.setdefault("cmk", cmk)
sys.modules.setdefault("cmk.server_side_calls", server_side_calls)
sys.modules["cmk.server_side_calls.v1"] = v1

PLUGIN = (
    Path(__file__).parents[1]
    / "src/switch_port_sync/server_side_calls/special_agent.py"
)
spec = importlib.util.spec_from_file_location("switch_port_sync_server_side", PLUGIN)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


COMPLETE_PARAMS = {
    "pair_name": "Switch pair 1",
    "host_a": "switch-1",
    "host_b": "switch-2",
    "service_regex": r"^Interface (?P<item>.+)$",
}


def test_complete_configuration_builds_explicit_command() -> None:
    commands = list(module._agent_arguments(COMPLETE_PARAMS, HostConfig(name="switch-1")))
    assert commands == [
        SpecialAgentCommand(
            command_arguments=[
                "--pair-name",
                "Switch pair 1",
                "--host-a",
                "switch-1",
                "--host-b",
                "switch-2",
                "--service-regex",
                r"^Interface (?P<item>.+)$",
            ]
        )
    ]


@pytest.mark.parametrize("missing_key", ["pair_name", "host_a", "host_b", "service_regex"])
def test_missing_required_configuration_is_rejected(missing_key: str) -> None:
    params = dict(COMPLETE_PARAMS)
    del params[missing_key]

    with pytest.raises(ValueError, match=missing_key):
        list(module._agent_arguments(params, HostConfig(name="switch-1")))


@pytest.mark.parametrize("empty_key", ["pair_name", "host_a", "host_b", "service_regex"])
def test_blank_required_configuration_is_rejected(empty_key: str) -> None:
    params = dict(COMPLETE_PARAMS)
    params[empty_key] = "   "

    with pytest.raises(ValueError, match=empty_key):
        list(module._agent_arguments(params, HostConfig(name="switch-1")))


def test_unrelated_host_does_not_run_agent() -> None:
    assert list(module._agent_arguments(COMPLETE_PARAMS, HostConfig(name="switch-3"))) == []
