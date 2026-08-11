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
        """Store result state, summary, and optional details exactly as emitted so unit tests can assert check behavior."""

        self.state = state
        self.summary = summary
        self.details = details


class Service:
    """Represent the minimal Checkmk service object needed to assert discovered item identities in isolated unit tests."""

    def __init__(self, item=None):
        """Store the optional service item exactly as the production discovery function supplied it for later assertions."""

        self.item = item


class Metric:
    """Represent the minimal Checkmk metric object required to validate emitted metric names and values in package tests."""

    def __init__(self, name, value):
        """Store the metric name and numeric value without applying any Checkmk rendering or unit conversion."""

        self.name = name
        self.value = value


class AgentSection:
    """Represent the AgentSection registration fields required to exercise parser registrations without importing a full Checkmk site."""

    def __init__(self, name, parse_function):
        """Store the section name and parser callable exactly as supplied by the production AgentSection registration."""

        self.name = name
        self.parse_function = parse_function


class CheckPlugin:
    """Represent a CheckPlugin registration by retaining its keyword arguments for focused contract assertions in tests."""

    def __init__(self, **kwargs):
        """Store the complete CheckPlugin keyword-argument mapping so tests can inspect defaults, rulesets, and callbacks."""

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


# Pytest discovers nested conftest files during collection, after the global
# pytest_sessionstart hook has already fired. Prepare the S2D namespace and API
# stub immediately at conftest import time so the full repository test suite
# cannot depend on which other package's Checkmk stub was imported first.
_package_root = Path(__file__).resolve().parents[1]
_package_src = str(_package_root / "src")
if _package_src not in sys.path:
    sys.path.insert(0, _package_src)
_install_cmk_stub()
