#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

import re
from json import loads, JSONDecodeError

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Metric,
    Result,
    Service,
    State,
    render,
)


OVERALL_ITEM = "Overall"

# Default mapping of actuator status strings to a monitoring state. Anything
# not listed here maps to UNKNOWN(3) instead of silently claiming OK.
DEFAULT_STATUS_MAP = {
    "UP": State.OK,
    "OUT_OF_SERVICE": State.WARN,
    "DOWN": State.CRIT,
    "UNKNOWN": State.UNKNOWN,
}

# Detail keys that carry a byte count and read nicer rendered as a size.
BYTE_KEYS = {"total", "free", "threshold", "used"}


def _flatten(components, prefix=""):
    """
    Flatten the (possibly nested) actuator 'components' tree into a flat
    mapping of service item -> {"status", "details"}. Nested composite
    indicators become "parent/child" items.
    """
    flat = {}
    for name, comp in components.items():
        if not isinstance(comp, dict):
            continue
        item = f"{prefix}{name}"
        status = comp.get("status")
        if status is not None:
            flat[item] = {
                "status": status,
                "details": comp.get("details") or {},
            }
        nested = comp.get("components")
        if isinstance(nested, dict):
            flat.update(_flatten(nested, prefix=f"{item}/"))
    return flat


def parse_spring_boot_actuator(string_table):
    """
    Read the single JSON line emitted by the special agent.
    """
    raw = "".join(row[0] for row in string_table if row)
    if not raw.strip():
        return None
    try:
        health = loads(raw)
    except JSONDecodeError:
        return None

    return {
        "overall": health.get("status"),
        "groups": health.get("groups") or [],
        "components": _flatten(health.get("components") or {}),
        "error": health.get("_error"),
    }


agent_section_spring_boot_actuator = AgentSection(
    name="spring_boot_actuator",
    parse_function=parse_spring_boot_actuator,
)


def discover_spring_boot_actuator(section):
    if section is None:
        return
    yield Service(item=OVERALL_ITEM)
    for item in section["components"]:
        yield Service(item=item)


def _status_map(params):
    """
    Merge the user supplied status overrides onto the built-in defaults.
    """
    mapping = dict(DEFAULT_STATUS_MAP)
    for entry in params.get("status_map") or []:
        mapping[str(entry["status"]).upper()] = State(entry["state"])
    return mapping


def _metric_name(key):
    """
    Turn an arbitrary detail key into a valid, unique-per-service metric name.
    """
    name = re.sub(r"[^a-zA-Z0-9_]", "_", key).strip("_").lower()
    if not name:
        name = "value"
    if name[0].isdigit():
        name = f"m_{name}"
    return name


def _render_detail(key, value):
    """
    Human readable representation of a single detail field.
    """
    if key in BYTE_KEYS and isinstance(value, (int, float)) and not isinstance(value, bool):
        return render.bytes(value)
    return str(value)


def check_spring_boot_actuator(item, params, section):
    if section is None:
        return

    mapping = _status_map(params)

    if item == OVERALL_ITEM:
        if section["error"]:
            yield Result(state=State.CRIT, summary=f"Agent error: {section['error']}")
            return
        components = section["components"]
        not_up = sorted(
            name for name, comp in components.items()
            if str(comp["status"]).upper() != "UP"
        )
        overall = section["overall"]
        state = mapping.get(str(overall).upper(), State.UNKNOWN)
        yield Result(
            state=state,
            summary=(f"Overall status: {overall}, {len(components)} components "
                     f"({len(components) - len(not_up)} UP, {len(not_up)} not UP)"),
        )
        if not_up:
            yield Result(
                state=State.OK,
                notice="Components not UP: " + ", ".join(not_up),
            )
        if section["groups"]:
            yield Result(
                state=State.OK,
                notice="Groups: " + ", ".join(map(str, section["groups"])),
            )
        return

    component = section["components"].get(item)
    if component is None:
        return

    status = component["status"]
    state = mapping.get(str(status).upper(), State.UNKNOWN)
    yield Result(state=state, summary=f"Status: {status}")

    seen_metrics = set()
    for key, value in component["details"].items():
        yield Result(state=State.OK, notice=f"{key}: {_render_detail(key, value)}")
        # Emit a metric for plain numeric fields so they can be graphed.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        name = _metric_name(key)
        if name in seen_metrics:
            continue
        seen_metrics.add(name)
        yield Metric(name, float(value))


check_plugin_spring_boot_actuator = CheckPlugin(
    name="spring_boot_actuator",
    service_name="Actuator %s",
    discovery_function=discover_spring_boot_actuator,
    check_function=check_spring_boot_actuator,
    check_default_parameters={},
    check_ruleset_name="spring_boot_actuator",
)
