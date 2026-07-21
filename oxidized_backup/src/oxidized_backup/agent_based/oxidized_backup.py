#!/usr/bin/env python3
"""Checkmk 2.4 check plug-in for Oxidized backup monitoring."""

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
_VALID_KINDS = frozenset({"central", "device"})


def parse_oxidized_backup(string_table: StringTable) -> Section:
    text = "".join(itertools.chain.from_iterable(string_table))
    if not text:
        return {"kind": "invalid", "error": "Agent plug-in returned an empty section"}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"kind": "invalid", "error": f"Invalid JSON from agent plug-in: {exc}"}
    if not isinstance(payload, dict):
        return {"kind": "invalid", "error": "Agent plug-in payload is not a JSON object"}
    if payload.get("schema_version") != 1:
        return {**payload, "error": "Unsupported oxidized_backup payload schema"}
    if payload.get("kind") not in _VALID_KINDS:
        return {**payload, "error": "Agent plug-in payload has an invalid kind"}
    return payload


def discover_oxidized_backup(section: Section) -> DiscoveryResult:
    kind = section.get("kind")
    if kind == "device":
        yield Service(item="backup")
    elif kind == "central":
        yield Service(item="backup inventory")
        yield Service(item="Git repository")
        yield Service(item="Git remote synchronization")


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return []


def _integer(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _age(now: int, timestamp: object) -> int | None:
    parsed = _integer(timestamp)
    if parsed is None or parsed <= 0:
        return None
    return max(0, now - parsed)


def _state_from_hint(value: object) -> State:
    hint = _integer(value)
    return {
        0: State.OK,
        1: State.WARN,
        2: State.CRIT,
        3: State.UNKNOWN,
    }.get(hint, State.UNKNOWN)


def _worst_state(states: Sequence[State]) -> State:
    if State.CRIT in states:
        return State.CRIT
    if State.UNKNOWN in states:
        return State.UNKNOWN
    if State.WARN in states:
        return State.WARN
    return State.OK


def _format_age(seconds: int | None) -> str:
    if seconds is None:
        return "unknown"
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def _policy(section: Section) -> Mapping[str, Any]:
    return _mapping(section.get("policy"))


def _collection_thresholds(section: Section) -> tuple[int | None, int | None]:
    policy = _policy(section)
    warning = _integer(policy.get("collection_warning_age_seconds"))
    critical = _integer(policy.get("collection_critical_age_seconds"))
    if warning is None or critical is None or warning <= 0 or critical <= warning:
        return None, None
    return warning, critical


def _device_check(section: Section) -> CheckResult:
    error = section.get("error")
    if error:
        yield Result(state=State.UNKNOWN, summary=str(error))
        return

    host_name = str(section.get("host_name") or "unknown host")
    if section.get("inventory_duplicate"):
        yield Result(
            state=State.UNKNOWN,
            summary=f"{host_name} appears more than once in the Checkmk Oxidized export",
        )
        return
    if section.get("api_ambiguous"):
        yield Result(
            state=State.UNKNOWN,
            summary=f"Multiple Oxidized nodes use the name {host_name}",
        )
        return
    api_error = section.get("api_error")
    if api_error:
        yield Result(
            state=State.UNKNOWN,
            summary=f"Oxidized API unavailable: {api_error}",
        )
    mapping_error = section.get("mapping_error")
    if mapping_error:
        yield Result(state=State.UNKNOWN, summary=str(mapping_error))

    oxidized = _mapping(section.get("oxidized"))
    if api_error:
        pass
    elif not oxidized.get("present"):
        yield Result(
            state=State.CRIT,
            summary="Device is exported by Checkmk but missing from Oxidized",
            details=f"Expected Oxidized node: {host_name}",
        )
    else:
        status = str(oxidized.get("status") or "unknown").lower()
        now = int(time.time())
        last_attempt_age = _age(now, oxidized.get("last_attempt_at"))
        last_success_age = _age(now, oxidized.get("last_success_at"))
        warning, critical = _collection_thresholds(section)
        details = (
            f"Status source: {oxidized.get('source', 'unknown')}\n"
            f"Last attempt age: {_format_age(last_attempt_age)}\n"
            f"Last success age: {_format_age(last_success_age)}\n"
            f"Persistent hook state: {'available' if oxidized.get('persistent_state') else 'not available'}"
        )
        error_reason = oxidized.get("last_error_reason")
        if error_reason:
            details += f"\nLast error: {error_reason}"

        if status == "success":
            if warning is None or critical is None:
                yield Result(
                    state=State.UNKNOWN,
                    summary="Collection age thresholds are missing or invalid",
                    details=details,
                )
            elif last_success_age is None:
                yield Result(
                    state=State.UNKNOWN,
                    summary="Oxidized reports success without a usable completion timestamp",
                    details=details,
                )
            elif last_success_age >= critical:
                yield Result(
                    state=State.CRIT,
                    summary=f"Last successful collection is {_format_age(last_success_age)} old",
                    details=details,
                )
            elif last_success_age >= warning:
                yield Result(
                    state=State.WARN,
                    summary=f"Last successful collection is {_format_age(last_success_age)} old",
                    details=details,
                )
            else:
                yield Result(
                    state=State.OK,
                    summary=f"Last collection successful {_format_age(last_success_age)} ago",
                    details=details,
                )
            if last_success_age is not None:
                if warning is not None and critical is not None:
                    yield Metric(
                        "oxidized_collection_age",
                        last_success_age,
                        levels=(warning, critical),
                    )
                else:
                    yield Metric("oxidized_collection_age", last_success_age)
        elif status == "never":
            yield Result(
                state=State.CRIT,
                summary="Oxidized has never completed a collection for this device",
                details=details,
            )
        elif status in {"no_connection", "timelimit", "fail", "failed"}:
            yield Result(
                state=State.CRIT,
                summary=f"Latest Oxidized collection failed with status {status}",
                details=details,
            )
        else:
            yield Result(
                state=State.UNKNOWN,
                summary=f"Unsupported or unresolved Oxidized status: {status}",
                details=details,
            )

    git = _mapping(section.get("git"))
    if git.get("error"):
        yield Result(state=State.UNKNOWN, summary=f"Git artifact cannot be verified: {git['error']}")
    elif not git.get("exists"):
        yield Result(
            state=State.CRIT,
            summary="No configuration artifact exists in the local Git repository",
            details=(
                f"Repository: {git.get('repository_id', 'unknown')}\n"
                f"Expected tree path: {git.get('path', 'unknown')}\n"
                f"Repository HEAD: {git.get('repository_head', 'unknown')}"
            ),
        )
    else:
        size = _integer(git.get("size"))
        if size is None:
            yield Result(state=State.UNKNOWN, summary="Git backup blob size is unavailable")
        elif size <= 0:
            yield Result(
                state=State.CRIT,
                summary="Configuration artifact in local Git is empty",
                details=f"Tree path: {git.get('path', 'unknown')}",
            )
        else:
            remote = _mapping(section.get("remote"))
            remote_note = str(remote.get("status") or "unknown")
            yield Result(
                state=State.OK,
                summary=f"Local Git backup exists ({size} bytes)",
                details=(
                    f"Repository: {git.get('repository_id', 'unknown')}\n"
                    f"Tree path: {git.get('path', 'unknown')}\n"
                    f"Blob: {git.get('oid', 'unknown')}\n"
                    f"Remote repository status: {remote_note}; evaluated centrally"
                ),
            )
            yield Metric("oxidized_backup_size", size)


def _inventory_check(section: Section) -> CheckResult:
    if section.get("error"):
        yield Result(state=State.UNKNOWN, summary=str(section["error"]))
        return
    inventory = _mapping(section.get("inventory"))
    if inventory.get("error"):
        yield Result(state=State.UNKNOWN, summary=str(inventory["error"]))
        return

    expected = _integer(inventory.get("expected")) or 0
    loaded = _integer(inventory.get("loaded")) or 0
    matched = _integer(inventory.get("matched")) or 0
    missing = [str(item) for item in _sequence(inventory.get("missing"))]
    orphans = [str(item) for item in _sequence(inventory.get("orphans"))]
    duplicate_api = [
        str(item) for item in _sequence(inventory.get("duplicate_oxidized_names"))
    ]
    inventory_errors = [str(item) for item in _sequence(inventory.get("errors"))]
    oxidized_errors = [str(item) for item in _sequence(inventory.get("oxidized_errors"))]

    if inventory.get("api_error"):
        yield Result(
            state=State.UNKNOWN,
            summary=f"Oxidized API unavailable: {inventory['api_error']}",
            details=f"Expected hosts from Checkmk export: {expected}",
        )
        return
    if inventory_errors or oxidized_errors:
        yield Result(
            state=State.UNKNOWN,
            summary="Inventory or Oxidized node data contains invalid records",
            details="\n".join([*inventory_errors, *oxidized_errors]),
        )
        return

    details = (
        f"Expected from Checkmk export: {expected}\n"
        f"Loaded by Oxidized: {loaded}\n"
        f"Matched: {matched}\n"
        f"Missing: {', '.join(missing) if missing else 'none'}\n"
        f"Orphaned in Oxidized: {', '.join(orphans) if orphans else 'none'}\n"
        f"Duplicate Oxidized names: {', '.join(duplicate_api) if duplicate_api else 'none'}"
    )
    if missing or duplicate_api:
        yield Result(
            state=State.CRIT,
            summary=(
                f"{expected} expected, {matched} matched, "
                f"{len(missing)} missing, {len(duplicate_api)} duplicate"
            ),
            details=details,
        )
    else:
        orphan_state = _integer(_policy(section).get("orphan_state")) or 0
        state = _state_from_hint(orphan_state if orphans else 0)
        yield Result(
            state=state,
            summary=f"{expected} expected, {matched} matched, {len(orphans)} orphaned",
            details=details,
        )

    if not inventory.get("hook_state_available"):
        yield Result(
            state=State.WARN,
            summary="Persistent Oxidized hook state is unavailable",
            details=str(inventory.get("hook_state_error") or "Configure the supplied Oxidized exec hook"),
        )
    else:
        yield Result(state=State.OK, summary="Persistent Oxidized hook state is available")

    yield Metric("oxidized_expected_nodes", expected)
    yield Metric("oxidized_loaded_nodes", loaded)
    yield Metric("oxidized_missing_nodes", len(missing))
    yield Metric("oxidized_orphan_nodes", len(orphans))


def _repository_check(section: Section) -> CheckResult:
    if section.get("monitor_state_error"):
        yield Result(
            state=State.UNKNOWN,
            summary=f"Monitor state cannot be persisted: {section['monitor_state_error']}",
        )
    repositories = [
        _mapping(item) for item in _sequence(section.get("repositories")) if isinstance(item, Mapping)
    ]
    if section.get("git_error"):
        yield Result(state=State.UNKNOWN, summary=str(section["git_error"]))
        return
    if not repositories:
        yield Result(state=State.UNKNOWN, summary="No Git repository results were returned")
        return

    missing_total = 0
    empty_total = 0
    expected_total = 0
    details: list[str] = []
    worst = State.OK
    for repo in repositories:
        repo_id = str(repo.get("id") or "unknown")
        expected = _integer(repo.get("expected_files")) or 0
        expected_total += expected
        missing = [str(item) for item in _sequence(repo.get("missing_files"))]
        empty = [str(item) for item in _sequence(repo.get("empty_files"))]
        missing_total += len(missing)
        empty_total += len(empty)
        fsck = _mapping(repo.get("fsck"))
        fsck_status = str(fsck.get("status") or "unknown")
        if not repo.get("valid"):
            worst = _worst_state([worst, _state_from_hint(repo.get("state_hint"))])
            details.append(f"{repo_id}: invalid or inaccessible ({repo.get('error', 'unknown error')})")
        elif missing or empty or fsck_status == "failed":
            worst = State.CRIT
            details.append(
                f"{repo_id}: {expected} expected, {len(missing)} missing, "
                f"{len(empty)} empty, fsck={fsck_status}"
            )
        elif fsck_status == "unknown" and worst != State.CRIT:
            worst = State.UNKNOWN
            details.append(f"{repo_id}: repository valid, fsck result unavailable")
        else:
            details.append(
                f"{repo_id}: HEAD {repo.get('head', 'unknown')}, {expected} expected, fsck={fsck_status}"
            )

    yield Result(
        state=worst,
        summary=(
            f"{len(repositories)} repository/repositories, {expected_total} expected artifacts, "
            f"{missing_total} missing, {empty_total} empty"
        ),
        details="\n".join(details),
    )
    yield Metric("oxidized_git_expected_files", expected_total)
    yield Metric("oxidized_git_missing_files", missing_total)
    yield Metric("oxidized_git_empty_files", empty_total)


def _remote_check(section: Section) -> CheckResult:
    repositories = [
        _mapping(item) for item in _sequence(section.get("repositories")) if isinstance(item, Mapping)
    ]
    if not repositories:
        yield Result(state=State.UNKNOWN, summary="No Git remote results were returned")
        return

    states: list[State] = []
    details: list[str] = []
    synced = 0
    for repo in repositories:
        repo_id = str(repo.get("id") or "unknown")
        remote = _mapping(repo.get("remote"))
        state = _state_from_hint(remote.get("state_hint"))
        states.append(state)
        status = str(remote.get("status") or "unknown")
        if status == "synced":
            synced += 1
            details.append(
                f"{repo_id}: synchronized on {remote.get('branch', 'unknown')} at "
                f"{str(remote.get('local_head', 'unknown'))[:12]}"
            )
        elif status == "mismatch":
            details.append(
                f"{repo_id}: local {str(remote.get('local_head', 'unknown'))[:12]} != "
                f"remote {str(remote.get('remote_head', 'unknown'))[:12]}, "
                f"mismatch since {remote.get('mismatch_since', 'unknown')}"
            )
        else:
            details.append(f"{repo_id}: {status}: {remote.get('error', 'no details')}")

    worst = _worst_state(states) if states else State.UNKNOWN
    yield Result(
        state=worst,
        summary=f"{synced} of {len(repositories)} Git remotes synchronized",
        details="\n".join(details),
    )
    yield Metric("oxidized_git_synced_repositories", synced)


def check_oxidized_backup(item: str, section: Section) -> CheckResult:
    if section.get("error"):
        yield Result(state=State.UNKNOWN, summary=str(section["error"]))
        return
    kind = section.get("kind")
    if item == "backup" and kind == "device":
        yield from _device_check(section)
    elif item == "backup inventory" and kind == "central":
        yield from _inventory_check(section)
    elif item == "Git repository" and kind == "central":
        yield from _repository_check(section)
    elif item == "Git remote synchronization" and kind == "central":
        yield from _remote_check(section)
    else:
        yield Result(state=State.UNKNOWN, summary="Service does not match the section payload")


agent_section_oxidized_backup = AgentSection(
    name="oxidized_backup",
    parse_function=parse_oxidized_backup,
)

check_plugin_oxidized_backup = CheckPlugin(
    name="oxidized_backup",
    service_name="Oxidized %s",
    discovery_function=discover_oxidized_backup,
    check_function=check_oxidized_backup,
)
