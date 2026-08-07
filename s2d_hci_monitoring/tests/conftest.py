"""Minimal Checkmk API stubs for isolated S2D/HCI behavior tests."""

from __future__ import annotations

import sys
import types
from pathlib import Path


class State:
    """Small state stand-in matching the values used by check tests."""

    OK = "OK"
    WARN = "WARN"
    CRIT = "CRIT"
    UNKNOWN = "UNKNOWN"


class Result:
    """Capture Checkmk result state and text for unit assertions."""

    def __init__(self, state, summary, details=None):
        """Store the supplied Checkmk result fields."""

        self.state = state
        self.summary = summary
        self.details = details


class Service:
    """Capture a discovered service item."""

    def __init__(self, item=None):
        """Store the optional service item."""

        self.item = item


class Metric:
    """Capture a metric name and numeric value."""

    def __init__(self, name, value):
        """Store metric fields."""

        self.name = name
        self.value = value


class AgentSection:
    """Capture AgentSection registration arguments."""

    def __init__(self, name, parse_function):
        """Store section registration fields."""

        self.name = name
        self.parse_function = parse_function


class CheckPlugin:
    """Capture CheckPlugin keyword arguments."""

    def __init__(self, **kwargs):
        """Store the complete registration dictionary."""

        self.kwargs = kwargs


def check_levels(value, levels_upper=None, levels_lower=None, metric_name=None, label=None, boundaries=None, render_func=None):
    """Implement the fixed-level subset used by package unit tests."""

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


def _install_cmk_stub() -> None:
    """Install the minimal `cmk.agent_based.v2` module required by tests."""

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


def pytest_sessionstart(session) -> None:
    """Prepare namespace import paths and Checkmk stubs before test collection."""

    del session
    package_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(package_root / "src"))
    _install_cmk_stub()
