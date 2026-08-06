"""Minimal Checkmk API stubs for isolated package behavior tests."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


class State:
    OK = "OK"
    WARN = "WARN"
    CRIT = "CRIT"
    UNKNOWN = "UNKNOWN"


class Result:
    def __init__(self, state, summary, details=None):
        self.state = state
        self.summary = summary
        self.details = details


class Service:
    def __init__(self, item=None):
        self.item = item


class Metric:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class AgentSection:
    def __init__(self, name, parse_function):
        self.name = name
        self.parse_function = parse_function


class CheckPlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def check_levels(value, levels_upper=None, levels_lower=None, metric_name=None, label=None, boundaries=None, render_func=None):
    del boundaries, render_func
    if metric_name:
        yield Metric(metric_name, value)
    if levels_upper and levels_upper[0] == "fixed":
        warn, crit = levels_upper[1]
        state = State.CRIT if value >= crit else State.WARN if value >= warn else State.OK
        yield Result(state, f"{label}: {value}")
    elif levels_lower and levels_lower[0] == "fixed":
        warn, crit = levels_lower[1]
        state = State.CRIT if value <= crit else State.WARN if value <= warn else State.OK
        yield Result(state, f"{label}: {value}")


def install_cmk_agent_based_stub():
    cmk = types.ModuleType("cmk")
    agent_based = types.ModuleType("cmk.agent_based")
    v2 = types.ModuleType("cmk.agent_based.v2")
    v2.AgentSection = AgentSection
    v2.CheckPlugin = CheckPlugin
    v2.Result = Result
    v2.Service = Service
    v2.State = State
    v2.Metric = Metric
    v2.check_levels = check_levels
    sys.modules.setdefault("cmk", cmk)
    sys.modules.setdefault("cmk.agent_based", agent_based)
    sys.modules["cmk.agent_based.v2"] = v2


def load_plugin(relative_path: str):
    install_cmk_agent_based_stub()
    package_root = Path(__file__).resolve().parents[1]
    module_path = package_root / relative_path
    module_name = "test_loaded_" + module_path.stem
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
