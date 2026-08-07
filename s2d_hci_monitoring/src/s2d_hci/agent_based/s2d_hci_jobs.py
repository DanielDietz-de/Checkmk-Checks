#!/usr/bin/env python3
"""Monitor bounded Storage Spaces Direct background-job progress."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Metric, Result, State

from .s2d_hci_protocol import DEFAULT_STATE_POLICY, Section, as_float, collector_error, discover_items, parse_protocol_objects, state_from_text

STATE_DEFAULTS = dict(DEFAULT_STATE_POLICY)


def parse_s2d_hci_storage_jobs(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse storage jobs with stable identities and explicit protocol validation."""

    return parse_protocol_objects(
        string_table,
        identity_fields=("identity", "name", "section"),
        display_fields=("name", "section"),
        state_fields=("job_state", "state", "success"),
        fallback_name="Storage job",
    )


agent_section_s2d_hci_storage_jobs = AgentSection(name="s2d_hci_storage_jobs", parse_function=parse_s2d_hci_storage_jobs)


def discover_s2d_hci_storage_jobs(section: Section):
    """Discover active storage jobs and synthetic collector-error services."""

    yield from discover_items(section)


def check_s2d_hci_storage_jobs(item: str, params: Mapping[str, object], section: Section):
    """Evaluate job state and emit a finite completion metric when available."""

    entry = section.get(item)
    if entry is None:
        yield Result(state=State.UNKNOWN, summary=f"Storage job {item!r} not found")
        return
    error = collector_error(entry)
    if error:
        yield Result(state=State.UNKNOWN, summary=f"Storage job collection failed: {error}", details=str(entry.details))
        return
    percent = as_float(entry.details.get("percent_complete"))
    if percent is not None:
        yield Metric("s2d_hci_storage_job_percent", percent)
    state = state_from_text(entry.state, params)
    if entry.state.strip().lower() == "running" and state == State.OK:
        state = State.WARN
    yield Result(
        state=state,
        summary=f"Job: {entry.name}, state: {entry.state}, complete: {percent if percent is not None else 'n/a'}",
        details=str(entry.details),
    )


check_plugin_s2d_hci_storage_jobs = CheckPlugin(
    name="s2d_hci_storage_jobs",
    service_name="S2D/HCI storage job %s",
    discovery_function=discover_s2d_hci_storage_jobs,
    check_function=check_s2d_hci_storage_jobs,
    check_default_parameters=STATE_DEFAULTS,
    check_ruleset_name="s2d_hci_state_policy",
)
