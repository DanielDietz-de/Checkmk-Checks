#!/usr/bin/env python3
"""Monitor S2D storage jobs and repair or resynchronization progress.

The parser accepts JSON lines from the read-only Windows collector. Invalid
records are ignored and malformed percentage values are treated as unavailable
rather than aborting the complete section.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Metric, Result, Service, State


@dataclass(frozen=True)
class StorageJob:
    """Normalized storage-job state and original collector details."""

    name: str
    job_state: str
    percent_complete: float | None
    details: Mapping[str, object]


Section = Mapping[str, StorageJob]


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_s2d_hci_storage_jobs(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse storage-job JSON lines into a name-indexed section."""

    parsed: dict[str, StorageJob] = {}
    for row in string_table:
        if not row:
            continue
        try:
            data = json.loads(" ".join(row))
        except json.JSONDecodeError:
            continue
        name = str(data.get("name") or "storage_job")
        parsed[name] = StorageJob(
            name=name,
            job_state=str(data.get("job_state") or "unknown"),
            percent_complete=_as_float(data.get("percent_complete")),
            details=data,
        )
    return parsed


agent_section_s2d_hci_storage_jobs = AgentSection(name="s2d_hci_storage_jobs", parse_function=parse_s2d_hci_storage_jobs)


def discover_s2d_hci_storage_jobs(section: Section):
    for item in section:
        yield Service(item=item)


def check_s2d_hci_storage_jobs(item: str, section: Section):
    if item not in section:
        yield Result(state=State.OK, summary="Storage job no longer present")
        return
    entry = section[item]
    state_text = entry.job_state.lower()
    if state_text in {"completed", "new", "running"}:
        state = State.OK if state_text != "running" else State.WARN
    elif state_text in {"suspended", "blocked"}:
        state = State.WARN
    elif state_text in {"failed", "stopped"}:
        state = State.CRIT
    else:
        state = State.UNKNOWN
    if entry.percent_complete is not None:
        yield Metric("s2d_hci_storage_job_percent", entry.percent_complete)
    yield Result(state=state, summary=f"State: {entry.job_state}, complete: {entry.percent_complete}", details=str(entry.details))


check_plugin_s2d_hci_storage_jobs = CheckPlugin(
    name="s2d_hci_storage_jobs",
    service_name="S2D/HCI storage job %s",
    discovery_function=discover_s2d_hci_storage_jobs,
    check_function=check_s2d_hci_storage_jobs,
)
