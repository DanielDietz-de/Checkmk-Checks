#!/usr/bin/env python3
"""Monitor explicit collector-health envelopes emitted by S2D/HCI collectors."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Result, Service, State

PROTOCOL_VERSION = 1


@dataclass(frozen=True)
class CollectorHealth:
    """Validated final status envelope for one physical collector invocation."""

    collector: str
    details: Mapping[str, object]
    error: str | None = None


Section = Mapping[str, CollectorHealth]


def _synthetic_health(index: int, message: str) -> CollectorHealth:
    """Create a visible parser-failure health record instead of dropping bad input."""

    return CollectorHealth(collector=f"parser-error-{index}", details={"success": False, "error": message}, error=message)


def parse_s2d_hci_collector_health(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse health envelopes and preserve malformed, duplicate, or unsupported rows."""

    parsed: dict[str, CollectorHealth] = {}
    for index, row in enumerate(string_table, start=1):
        if not row:
            continue
        raw = " ".join(row)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            synthetic = _synthetic_health(index, f"Malformed collector-health JSON: {exc.msg}")
            parsed[synthetic.collector] = synthetic
            continue
        if not isinstance(data, Mapping):
            synthetic = _synthetic_health(index, "Collector-health row is not a JSON object")
            parsed[synthetic.collector] = synthetic
            continue
        protocol = data.get("protocol_version")
        collector = str(data.get("collector") or f"parser-error-{index}")
        error = None
        if protocol != PROTOCOL_VERSION:
            error = f"Unsupported collector protocol version: {protocol!r}"
        elif not str(data.get("run_id") or "").strip():
            error = "Collector-health row has no run_id"
        if collector in parsed:
            collector = f"duplicate-{collector}-{index}"
            error = error or "Duplicate collector-health row"
        parsed[collector] = CollectorHealth(collector=collector, details=dict(data), error=error)
    return parsed


agent_section_s2d_hci_collector_health = AgentSection(
    name="s2d_hci_collector_health",
    parse_function=parse_s2d_hci_collector_health,
)


def discover_s2d_hci_collector_health(section: Section):
    """Discover one health service for every collector or parser error row."""

    for item in section:
        yield Service(item=item)


def _explicit_bool(value: object) -> bool | None:
    """Return an explicit Boolean value without coercing arbitrary strings."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return None


def check_s2d_hci_collector_health(item: str, section: Section):
    """Report failed, incomplete, truncated, disabled, standby, or healthy runs."""

    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"Collector health {item!r} not found")
        return
    entry = section[item]
    if entry.error:
        yield Result(state=State.UNKNOWN, summary=entry.error, details=str(entry.details))
        return

    details = entry.details
    success = _explicit_bool(details.get("success"))
    complete = _explicit_bool(details.get("complete"))
    truncated = _explicit_bool(details.get("truncated"))
    role = str(details.get("role") or "unknown")
    errors = details.get("errors")
    error_text = "; ".join(str(value) for value in errors) if isinstance(errors, list) else str(errors or "")

    # Failure/completeness flags describe the collector invocation itself and must
    # win over a fallback role. In particular, malformed configuration uses safe
    # defaults that disable virtualization while marking the run failed/incomplete.
    if success is False or complete is False or truncated is True:
        summary = "Collector run failed or incomplete"
        if error_text:
            summary += f": {error_text}"
        yield Result(state=State.CRIT, summary=summary, details=str(details))
        return
    if success is not True or complete is not True or truncated is not False:
        yield Result(state=State.UNKNOWN, summary="Collector health envelope is incomplete", details=str(details))
        return
    if role == "disabled":
        yield Result(state=State.OK, summary="Collector intentionally disabled by configuration", details=str(details))
        return

    elapsed_ms = details.get("elapsed_ms")
    records = details.get("record_count")
    output_bytes = details.get("output_bytes")
    yield Result(
        state=State.OK,
        summary=f"Role: {role}, records: {records}, bytes: {output_bytes}, elapsed: {elapsed_ms} ms",
        details=str(details),
    )


check_plugin_s2d_hci_collector_health = CheckPlugin(
    name="s2d_hci_collector_health",
    service_name="S2D/HCI collector %s",
    discovery_function=discover_s2d_hci_collector_health,
    check_function=check_s2d_hci_collector_health,
)
