#!/usr/bin/env python3
"""Agent-based parsing and initial checks for Synology Active Backup for Microsoft 365."""

from __future__ import annotations

import itertools
import json
import time
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Any]
Job = Mapping[str, Any]

_STATUS_STATE = {
    1: State.OK,
    2: State.WARN,
    3: State.OK,
    6: State.CRIT,
    8: State.WARN,
    9: State.CRIT,
    10: State.UNKNOWN,
}
_STATUS_NAME = {
    1: "OK",
    2: "Warning",
    3: "Running",
    6: "Failed",
    8: "No data",
    9: "Database missing",
    10: "Unknown",
}


def parse_synology_active_backup_m365(string_table: StringTable) -> Section:
    text = "".join(itertools.chain.from_iterable(string_table))
    if not text:
        return {"error": "Special agent returned an empty section", "health": {}, "jobs": [], "sources": []}

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return {
            "error": f"Invalid JSON from special agent: {exc}",
            "health": {},
            "jobs": [],
            "sources": [],
        }

    if not isinstance(payload, dict):
        return {"error": "Special agent payload is not a JSON object", "health": {}, "jobs": [], "sources": []}

    health = payload.get("health")
    jobs = payload.get("jobs")
    sources = payload.get("sources")
    if not isinstance(health, dict) or not isinstance(jobs, list) or not isinstance(sources, list):
        return {
            "error": "Special agent payload has invalid health/jobs/sources types",
            "health": health if isinstance(health, dict) else {},
            "jobs": jobs if isinstance(jobs, list) else [],
            "sources": sources if isinstance(sources, list) else [],
        }

    return payload


def _m365_jobs(section: Section) -> Sequence[Job]:
    jobs = section.get("jobs", [])
    if not isinstance(jobs, list):
        return []
    return [
        job
        for job in jobs
        if isinstance(job, Mapping) and str(job.get("product", "")).lower() == "m365"
    ]


def _m365_sources(section: Section) -> Sequence[Mapping[str, Any]]:
    sources = section.get("sources", [])
    if not isinstance(sources, list):
        return []
    return [
        source
        for source in sources
        if isinstance(source, Mapping) and str(source.get("product", "")).lower() == "m365"
    ]


def discover_synology_active_backup_m365(section: Section) -> DiscoveryResult:
    # Always keep a collector-health service so a disappearing source cannot
    # silently remove all monitoring.
    yield Service(item="Health")

    seen: set[str] = set()
    for job in _m365_jobs(section):
        task_id = str(job.get("task_id", "")).strip()
        if not task_id or task_id in seen:
            continue
        seen.add(task_id)
        yield Service(item=task_id)


def _health_check(section: Section) -> CheckResult:
    error = section.get("error")
    if error:
        yield Result(state=State.UNKNOWN, summary=str(error))
        return

    health = section.get("health", {})
    if not isinstance(health, Mapping):
        yield Result(state=State.UNKNOWN, summary="Collector health object is missing")
        return

    sources = _m365_sources(section)
    if not sources:
        yield Result(state=State.CRIT, summary="No Microsoft 365 data source reported by collector")
        return

    missing_sources = [source for source in sources if source.get("found") is not True]
    if missing_sources:
        errors = [str(source.get("error", "source not found")) for source in missing_sources]
        yield Result(
            state=State.CRIT,
            summary=f"{len(missing_sources)} Microsoft 365 source(s) unavailable",
            details="\n".join(errors),
        )
        return

    collector_errors = health.get("collector_errors", [])
    if health.get("ok") is not True:
        details = "\n".join(str(value) for value in collector_errors) if isinstance(collector_errors, list) else str(collector_errors)
        yield Result(
            state=State.CRIT,
            summary="Collector reports unhealthy status",
            details=details or "health.ok is not true",
        )
        return

    collected_unix = health.get("collected_unix")
    if isinstance(collected_unix, (int, float)) and collected_unix > 0:
        age = max(0.0, time.time() - float(collected_unix))
        yield Metric("synology_m365_collector_age", age)
        if age > 1800:
            yield Result(state=State.CRIT, summary=f"Collector data stale: {age / 60:.0f} minutes old")
            return
        if age > 900:
            yield Result(state=State.WARN, summary=f"Collector data old: {age / 60:.0f} minutes old")
            return

    jobs = _m365_jobs(section)
    if not jobs:
        yield Result(state=State.WARN, summary="Collector healthy, but no Microsoft 365 jobs found")
        return

    yield Result(
        state=State.OK,
        summary=f"Collector healthy, {len(jobs)} Microsoft 365 job(s), {len(sources)} source(s)",
    )


def _find_job(item: str, section: Section) -> Job | None:
    for job in _m365_jobs(section):
        if str(job.get("task_id", "")).strip() == item:
            return job
    return None


def _number(job: Job, key: str) -> float | None:
    value = job.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value >= 0:
        return float(value)
    return None


def _job_check(item: str, section: Section) -> CheckResult:
    job = _find_job(item, section)
    if job is None:
        yield Result(state=State.UNKNOWN, summary="Microsoft 365 backup task data is missing")
        return

    try:
        status = int(job.get("status", 10))
    except (TypeError, ValueError):
        status = 10

    state = _STATUS_STATE.get(status, State.UNKNOWN)
    status_name = _STATUS_NAME.get(status, f"Unmapped ({status})")
    job_name = str(job.get("job_name", "")).strip() or "unnamed/redacted"
    raw_status = str(job.get("raw_status", "")).strip()
    error_code = str(job.get("error_code", "")).strip()

    summary = f"{job_name}: {status_name}"
    if raw_status:
        summary += f" ({raw_status})"
    if error_code:
        summary += f", error {error_code}"

    details = [f"Task ID: {item}", f"Job name: {job_name}"]
    for key, label in (
        ("start_time", "Start"),
        ("end_time", "End"),
        ("last_success_time", "Last success"),
    ):
        value = job.get(key)
        if value:
            details.append(f"{label}: {value}")

    last_success_age = _number(job, "last_success_age_seconds")
    if last_success_age is not None:
        yield Metric("synology_m365_last_success_age", last_success_age)
        details.append(f"Last success age: {last_success_age / 3600:.2f} h")

    backup_age = _number(job, "age_seconds")
    if backup_age is not None:
        yield Metric("synology_m365_backup_age", backup_age)

    runtime = _number(job, "runtime_seconds")
    if runtime is not None:
        yield Metric("synology_m365_runtime", runtime)
        details.append(f"Runtime: {runtime:.0f} s")

    transferred = _number(job, "transferred_size")
    if transferred is not None:
        yield Metric("synology_m365_transferred_size", transferred)
        details.append(f"Transferred: {transferred:.0f} bytes")

    if job.get("has_data") is False and state == State.OK:
        state = State.WARN
        summary += ", collector marks job as having no data"

    yield Result(state=state, summary=summary, details="\n".join(details))


def check_synology_active_backup_m365(item: str, section: Section) -> CheckResult:
    if item == "Health":
        yield from _health_check(section)
        return

    error = section.get("error")
    if error:
        yield Result(state=State.UNKNOWN, summary=str(error))
        return

    yield from _job_check(item, section)


agent_section_synology_active_backup_m365 = AgentSection(
    name="synology_active_backup_m365",
    parse_function=parse_synology_active_backup_m365,
)

check_plugin_synology_active_backup_m365 = CheckPlugin(
    name="synology_active_backup_m365",
    service_name="Synology M365 Backup %s",
    discovery_function=discover_synology_active_backup_m365,
    check_function=check_synology_active_backup_m365,
)
