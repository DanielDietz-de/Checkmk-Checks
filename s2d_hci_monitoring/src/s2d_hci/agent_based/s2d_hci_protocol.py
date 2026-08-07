#!/usr/bin/env python3
"""Shared parser and state-policy helpers for the S2D/HCI Checkmk plug-ins.

Collectors use protocol version 1 and attach a run identifier to every JSON
record.  This module validates those fields, preserves malformed/duplicate
records as explicit synthetic objects, and provides conservative state mapping
for all check plug-ins in the package.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import Service, State

PROTOCOL_VERSION = 1
DEFAULT_STATE_POLICY: Mapping[str, str] = {
    "degraded_state": "warn",
    "paused_state": "warn",
    "draining_state": "warn",
    "offline_state": "crit",
    "unknown_state": "unknown",
}


@dataclass(frozen=True)
class ProtocolObject:
    """Normalized protocol record plus its original collector detail mapping."""

    identity: str
    name: str
    state: str
    details: Mapping[str, object]
    issue: str | None = None


Section = Mapping[str, ProtocolObject]


def _stable_suffix(value: str) -> str:
    """Return a short deterministic digest used only for synthetic service keys."""

    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:12]


def _issue_object(index: int, issue: str, raw: str = "") -> ProtocolObject:
    """Create a synthetic UNKNOWN object so malformed input remains visible."""

    digest = _stable_suffix(f"{index}:{issue}:{raw}")
    details: dict[str, object] = {
        "protocol_version": PROTOCOL_VERSION,
        "run_id": "parser",
        "success": False,
        "error": issue,
    }
    if raw:
        details["raw_preview"] = raw[:256]
    identity = f"parser-error-{digest}"
    return ProtocolObject(identity=identity, name="Parser error", state="unknown", details=details, issue=issue)


def _field(data: Mapping[str, object], names: Sequence[str]) -> object | None:
    """Return the first non-empty field using exact then normalized name matching."""

    for name in names:
        value = data.get(name)
        if value not in (None, ""):
            return value
    normalized = {str(key).replace("_", "").lower(): value for key, value in data.items()}
    for name in names:
        value = normalized.get(name.replace("_", "").lower())
        if value not in (None, ""):
            return value
    return None


def parse_protocol_objects(
    string_table: Sequence[Sequence[str]],
    *,
    identity_fields: Sequence[str] = ("identity", "name"),
    display_fields: Sequence[str] = ("name", "friendly_name", "filesystem_label", "subsystem"),
    state_fields: Sequence[str] = (
        "state",
        "health_status",
        "operational_status",
        "status",
        "severity",
        "job_state",
        "quorum_resource_state",
    ),
    fallback_name: str = "S2D/HCI object",
) -> Section:
    """Parse versioned JSON rows without silently dropping malformed or duplicate data."""

    parsed: dict[str, ProtocolObject] = {}
    for index, row in enumerate(string_table, start=1):
        if not row:
            continue
        raw = " ".join(row)
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            issue = _issue_object(index, f"Malformed JSON: {exc.msg}", raw)
            parsed[issue.identity] = issue
            continue
        if not isinstance(decoded, Mapping):
            issue = _issue_object(index, "Collector record is not a JSON object", raw)
            parsed[issue.identity] = issue
            continue

        data = dict(decoded)
        protocol = _field(data, ("protocol_version",))
        run_id = _field(data, ("run_id",))
        if protocol != PROTOCOL_VERSION:
            issue = _issue_object(index, f"Unsupported or missing protocol version: {protocol!r}", raw)
            parsed[issue.identity] = issue
            continue
        if not isinstance(run_id, str) or not run_id.strip():
            issue = _issue_object(index, "Missing run_id in collector record", raw)
            parsed[issue.identity] = issue
            continue

        identity_value = _field(data, identity_fields)
        if identity_value in (None, ""):
            if _is_false(_field(data, ("success",))):
                identity_value = f"collector-error-{index}"
            else:
                issue = _issue_object(index, "Record has no stable identity", raw)
                parsed[issue.identity] = issue
                continue
        identity = str(identity_value).strip()
        display = _field(data, display_fields)
        name = str(display).strip() if display not in (None, "") else fallback_name
        state_value = _field(data, state_fields)
        state = str(state_value).strip() if state_value not in (None, "") else "unknown"
        object_record = ProtocolObject(identity=identity, name=name, state=state, details=data)

        if identity in parsed:
            duplicate = _issue_object(index, f"Duplicate stable identity {identity!r}", raw)
            parsed[duplicate.identity] = duplicate
            continue
        parsed[identity] = object_record
    return parsed


def discover_items(section: Section):
    """Discover one Checkmk service for every normalized or synthetic record."""

    for item in section:
        yield Service(item=item)


def as_float(value: object) -> float | None:
    """Return a finite float or ``None`` for absent, malformed, or non-finite input."""

    if value is None:
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if math.isfinite(converted) else None


def as_bool(value: object) -> bool | None:
    """Parse explicit Boolean collector values without relying on truthiness."""

    if isinstance(value, bool):
        return value
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "enabled"}:
        return True
    if normalized in {"false", "0", "no", "disabled"}:
        return False
    return None


def _is_false(value: object) -> bool:
    """Return whether a structured collector success value explicitly means false."""

    return as_bool(value) is False


def collector_error(entry: ProtocolObject) -> str | None:
    """Return an actionable parser or collector error carried by one object."""

    if entry.issue:
        return entry.issue
    if _is_false(entry.details.get("success")):
        return str(entry.details.get("error") or "Collector reported an unspecified failure")
    return None


def state_from_severity(value: object, default: State = State.UNKNOWN) -> State:
    """Convert a ruleset severity name into a Checkmk state value."""

    normalized = str(value or "").strip().lower()
    return {
        "ok": State.OK,
        "warn": State.WARN,
        "crit": State.CRIT,
        "unknown": State.UNKNOWN,
    }.get(normalized, default)


def state_from_text(value: object, params: Mapping[str, object] | None = None) -> State:
    """Map Microsoft state text through the configurable conservative state policy."""

    policy = dict(DEFAULT_STATE_POLICY)
    if params:
        for key in DEFAULT_STATE_POLICY:
            if key in params:
                policy[key] = str(params[key])

    normalized = str(value or "").strip().lower()
    if normalized in {
        "ok",
        "online",
        "up",
        "running",
        "healthy",
        "enabled",
        "succeeded",
        "operating normally",
        "normal",
        "true",
        "completed",
        "new",
    }:
        return State.OK
    if any(token in normalized for token in ("drain", "resynchron")):
        return state_from_severity(policy["draining_state"])
    if normalized in {"paused", "saved", "suspended"}:
        return state_from_severity(policy["paused_state"])
    if any(token in normalized for token in ("warn", "degraded", "incomplete", "stressed", "blocked")):
        return state_from_severity(policy["degraded_state"])
    if any(token in normalized for token in ("off", "down", "failed", "error", "critical", "detached", "lost", "notfound", "false", "stopped")):
        return state_from_severity(policy["offline_state"])
    return state_from_severity(policy["unknown_state"])
