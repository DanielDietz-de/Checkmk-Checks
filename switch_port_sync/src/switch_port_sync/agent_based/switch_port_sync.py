#!/usr/bin/env python3

from __future__ import annotations

import itertools
import json
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Any]
_UNRESOLVED_STATES = frozenset({"missing", "stale", "unknown"})
_REQUIRED_METADATA = ("pair_name", "host_a", "host_b", "service_regex")


def parse_switch_port_sync(string_table: StringTable) -> Section:
    text = "".join(itertools.chain.from_iterable(string_table))
    if not text:
        return {"records": [], "error": "Special agent returned an empty section"}

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"records": [], "error": f"Invalid JSON from special agent: {exc}"}

    if not isinstance(payload, dict):
        return {"records": [], "error": "Special agent payload is not a JSON object"}

    records = payload.get("records", [])
    if not isinstance(records, list):
        return {**payload, "records": [], "error": "Special agent records are not a list"}

    return payload


def _records(section: Section) -> Sequence[Mapping[str, Any]]:
    records = section.get("records", [])
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, Mapping)]


def _configuration_error(section: Section) -> str | None:
    invalid = [
        key
        for key in _REQUIRED_METADATA
        if not isinstance(section.get(key), str) or not str(section[key]).strip()
    ]
    if invalid:
        return "Special agent payload is missing required configuration metadata: " + ", ".join(
            invalid
        )
    return None


def _record_state(record: Mapping[str, Any], member: str) -> str:
    member_data = record.get(member, {})
    if not isinstance(member_data, Mapping):
        return "unknown"
    return str(member_data.get("state", "unknown"))


def _is_discovery_candidate(record: Mapping[str, Any]) -> bool:
    """Monitor pairs that have at least one confirmed-up member at discovery.

    This catches an already asymmetric pair immediately while excluding ports
    that are down on both switches and therefore normally unused.
    """

    return _record_state(record, "host_a") == "up" or _record_state(record, "host_b") == "up"


def discover_switch_port_sync(section: Section) -> DiscoveryResult:
    # The pair-level service keeps configuration and Livestatus failures visible
    # even when no port-level service can be discovered.
    yield Service(item="Pair status")

    if section.get("error") or _configuration_error(section):
        return

    seen: set[str] = set()
    for record in _records(section):
        item = record.get("item")
        if not isinstance(item, str) or not item or item in seen:
            continue
        if _is_discovery_candidate(record):
            seen.add(item)
            yield Service(item=item)


def _find_record(item: str, section: Section) -> Mapping[str, Any] | None:
    for record in _records(section):
        if record.get("item") == item:
            return record
    return None


def _pair_status(section: Section) -> CheckResult:
    error = section.get("error")
    if error:
        yield Result(state=State.UNKNOWN, summary=str(error))
        return

    configuration_error = _configuration_error(section)
    if configuration_error:
        yield Result(state=State.UNKNOWN, summary=configuration_error)
        return

    pair_name = str(section["pair_name"])
    records = _records(section)
    if not records:
        yield Result(
            state=State.UNKNOWN,
            summary=f"{pair_name}: no matching interface services found",
        )
        return

    candidates = sum(_is_discovery_candidate(record) for record in records)
    up_up = sum(
        _record_state(record, "host_a") == "up" and _record_state(record, "host_b") == "up"
        for record in records
    )
    asymmetric = sum(
        {_record_state(record, "host_a"), _record_state(record, "host_b")} == {"up", "down"}
        for record in records
    )
    unresolved = sum(
        _record_state(record, "host_a") in _UNRESOLVED_STATES
        or _record_state(record, "host_b") in _UNRESOLVED_STATES
        for record in records
    )

    yield Result(
        state=State.OK,
        summary=f"{pair_name}: {len(records)} mapped, {candidates} discovery candidate(s)",
        details=(
            f"Current up/up pairs: {up_up}\n"
            f"Current asymmetric up/down pairs: {asymmetric}\n"
            f"Pairs with missing, stale, or unknown data: {unresolved}"
        ),
    )


def check_switch_port_sync(item: str, section: Section) -> CheckResult:
    if item == "Pair status":
        yield from _pair_status(section)
        return

    error = section.get("error")
    if error:
        yield Result(state=State.UNKNOWN, summary=str(error))
        return

    configuration_error = _configuration_error(section)
    if configuration_error:
        yield Result(state=State.UNKNOWN, summary=configuration_error)
        return

    record = _find_record(item, section)
    if record is None:
        yield Result(state=State.UNKNOWN, summary="Interface pair data is missing")
        return

    pair_name = str(section["pair_name"])
    expected_name_a = str(section["host_a"])
    expected_name_b = str(section["host_b"])
    host_a = record.get("host_a", {})
    host_b = record.get("host_b", {})
    if not isinstance(host_a, Mapping) or not isinstance(host_b, Mapping):
        yield Result(state=State.UNKNOWN, summary="Malformed interface pair data")
        return

    name_a = host_a.get("name")
    name_b = host_b.get("name")
    if name_a != expected_name_a or name_b != expected_name_b:
        yield Result(
            state=State.UNKNOWN,
            summary="Interface pair data does not match the configured switch names",
        )
        return

    state_a = str(host_a.get("state", "unknown"))
    state_b = str(host_b.get("state", "unknown"))
    summary = f"{expected_name_a}: {state_a}, {expected_name_b}: {state_b}"
    details = (
        f"Pair: {pair_name}\n"
        f"{expected_name_a}: {host_a.get('reason', 'no reason available')}\n"
        f"{expected_name_b}: {host_b.get('reason', 'no reason available')}"
    )

    # Missing, stale, or unparseable source data is UNKNOWN. CRIT is reserved
    # for a confirmed operational-state failure.
    if state_a in _UNRESOLVED_STATES or state_b in _UNRESOLVED_STATES:
        yield Result(state=State.UNKNOWN, summary=summary, details=details)
    elif state_a == "up" and state_b == "up":
        yield Result(state=State.OK, summary=summary, details=details)
    else:
        # One down or both down are CRIT for every accepted discovery service.
        yield Result(state=State.CRIT, summary=summary, details=details)


agent_section_switch_port_sync = AgentSection(
    name="switch_port_sync",
    parse_function=parse_switch_port_sync,
)

check_plugin_switch_port_sync = CheckPlugin(
    name="switch_port_sync",
    service_name="Switch port sync %s",
    discovery_function=discover_switch_port_sync,
    check_function=check_switch_port_sync,
)
