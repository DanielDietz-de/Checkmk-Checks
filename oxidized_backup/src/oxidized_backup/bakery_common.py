#!/usr/bin/env python3
"""Pure helpers shared by the oxidized_backup Bakery plug-in and tests."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

DEFAULT_INTERVAL = 300
HOOK_HELPER_PATH = "/usr/bin/oxidized_backup_hook"
CONFIG_PATH = "/etc/check_mk/oxidized_backup.json"
HOOK_REFERENCE_PATH = "/etc/check_mk/oxidized_backup-hook.yml"

_USERNAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*[$]?$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _sequence(value: object, label: str) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    raise ValueError(f"{label} must be a sequence")


def _required_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    text = value.strip()
    if any(character in text for character in ("\x00", "\r", "\n")):
        raise ValueError(f"{label} contains forbidden control characters")
    return text


def _absolute_path(value: object, label: str) -> str:
    text = _required_string(value, label)
    if not Path(text).is_absolute():
        raise ValueError(f"{label} must be an absolute path")
    return text


def _positive_int(value: object, label: str, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    number = int(value)
    if number < minimum:
        raise ValueError(f"{label} must be >= {minimum}")
    return number


def _deployment(value: object) -> tuple[str, int | None]:
    if isinstance(value, (tuple, list)) and value:
        mode = str(value[0])
        raw_interval = value[1] if len(value) > 1 else None
    else:
        mode = str(value or "cached")
        raw_interval = None
    if mode not in {"sync", "cached", "do_not_deploy"}:
        raise ValueError(f"Unsupported deployment mode: {mode}")
    if mode == "cached":
        return mode, _positive_int(raw_interval or DEFAULT_INTERVAL, "deployment interval")
    return mode, None


def _auth(value: object) -> dict[str, Any] | None:
    if value in (None, "", "none"):
        return None
    if isinstance(value, (tuple, list)) and value:
        mode = str(value[0])
        settings = value[1] if len(value) > 1 else None
    else:
        raise ValueError("Authentication must be a cascading choice")
    if mode == "none":
        return None
    auth_settings = _mapping(settings, "authentication settings")
    if mode == "bearer":
        return {
            "type": "bearer",
            "token_file": _absolute_path(auth_settings.get("token_file"), "token file"),
        }
    if mode == "basic":
        return {
            "type": "basic",
            "username": _required_string(auth_settings.get("username"), "basic username"),
            "password_file": _absolute_path(
                auth_settings.get("password_file"), "basic password file"
            ),
        }
    raise ValueError(f"Unsupported authentication mode: {mode}")


def _endpoint(value: object, label: str, *, allow_file: bool) -> dict[str, Any]:
    source = _mapping(value, label)
    url = _required_string(source.get("url"), f"{label}.url")
    allowed_prefixes = (
        ("http://", "https://", "file://")
        if allow_file
        else ("http://", "https://")
    )
    if not url.startswith(allowed_prefixes):
        raise ValueError(f"{label}.url uses an unsupported scheme")
    result: dict[str, Any] = {
        "url": url,
        "timeout_seconds": _positive_int(
            source.get("timeout_seconds", 10), f"{label}.timeout_seconds"
        ),
        "max_response_bytes": _positive_int(
            source.get("max_response_bytes", 4 * 1024 * 1024),
            f"{label}.max_response_bytes",
            minimum=1024,
        ),
    }
    ca_file = source.get("ca_file")
    if ca_file:
        result["ca_file"] = _absolute_path(ca_file, f"{label}.ca_file")
    if source.get("allow_insecure_http") is True:
        result["allow_insecure_http"] = True
    auth = _auth(source.get("auth"))
    if auth:
        result["auth"] = auth
    return result


def _group_mapping(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        if value == "*":
            return "*"
        return _required_string(value, "repository group")
    if isinstance(value, (tuple, list)) and value:
        mode = str(value[0])
        payload = value[1] if len(value) > 1 else None
        if mode == "ungrouped":
            return None
        if mode == "wildcard":
            return "*"
        if mode == "named":
            return _required_string(payload, "repository group")
    raise ValueError("Invalid repository group mapping")


def _repository(value: object, index: int) -> dict[str, Any]:
    source = _mapping(value, f"repository {index}")
    repository_id = _required_string(source.get("id"), f"repository {index}.id")
    if not _IDENTIFIER_RE.fullmatch(repository_id):
        raise ValueError(f"repository {index}.id contains unsupported characters")
    groups = [
        _group_mapping(item) for item in _sequence(source.get("groups"), "groups")
    ]
    if not groups:
        raise ValueError(f"repository {repository_id} requires at least one group mapping")
    normalized_group_keys = ["<ungrouped>" if item is None else item for item in groups]
    if len(set(normalized_group_keys)) != len(normalized_group_keys):
        raise ValueError(f"repository {repository_id} contains duplicate group mappings")
    result: dict[str, Any] = {
        "id": repository_id,
        "path": _absolute_path(source.get("path"), f"repository {repository_id}.path"),
        "groups": groups,
        "single_repo": bool(source.get("single_repo", True)),
        "remote": _required_string(
            source.get("remote", "origin"), f"repository {repository_id}.remote"
        ),
        "command_timeout_seconds": _positive_int(
            source.get("command_timeout_seconds", 30),
            f"repository {repository_id}.command_timeout_seconds",
        ),
        "fsck_timeout_seconds": _positive_int(
            source.get("fsck_timeout_seconds", 120),
            f"repository {repository_id}.fsck_timeout_seconds",
        ),
    }
    branch = source.get("branch")
    if branch:
        result["branch"] = _required_string(
            branch, f"repository {repository_id}.branch"
        )
    return result


def normalize_rule(conf: object) -> tuple[str, int | None, dict[str, Any]]:
    """Normalize a Rulesets API consumer value into the collector JSON model."""

    source = _mapping(conf, "Bakery configuration")
    mode, interval = _deployment(source.get("deployment", ("cached", DEFAULT_INTERVAL)))

    state = _mapping(source.get("state"), "state")
    git = _mapping(source.get("git"), "git")
    policy = _mapping(source.get("policy"), "policy")

    run_as_user = _required_string(git.get("run_as_user"), "git.run_as_user")
    if not _USERNAME_RE.fullmatch(run_as_user) or run_as_user == "root":
        raise ValueError("git.run_as_user must be a valid unprivileged account name")

    raw_repositories = _sequence(git.get("repositories"), "git.repositories")
    repositories = [
        _repository(item, index) for index, item in enumerate(raw_repositories)
    ]
    if not repositories:
        raise ValueError("At least one Git repository is required")
    repository_ids = [repository["id"] for repository in repositories]
    if len(set(repository_ids)) != len(repository_ids):
        raise ValueError("Git repository IDs must be unique")
    if sum("*" in repository["groups"] for repository in repositories) > 1:
        raise ValueError("Only one repository may use the wildcard group mapping")

    warning_age = _positive_int(
        policy.get("collection_warning_age_seconds"),
        "policy.collection_warning_age_seconds",
    )
    critical_age = _positive_int(
        policy.get("collection_critical_age_seconds"),
        "policy.collection_critical_age_seconds",
    )
    if critical_age <= warning_age:
        raise ValueError("Critical collection age must be greater than warning age")

    orphan_raw = policy.get("orphan_state", "warn")
    orphan_state = {"ok": 0, "warn": 1, "crit": 2, 0: 0, 1: 1, 2: 2}.get(
        orphan_raw
    )
    if orphan_state is None:
        raise ValueError("policy.orphan_state must be OK, WARN, or CRIT")

    normalized = {
        "inventory": _endpoint(source.get("inventory"), "inventory", allow_file=True),
        "oxidized": _endpoint(source.get("oxidized"), "oxidized", allow_file=False),
        "state": {
            "hook_state_file": _absolute_path(
                state.get("hook_state_file"), "state.hook_state_file"
            ),
            "monitor_state_file": _absolute_path(
                state.get("monitor_state_file"), "state.monitor_state_file"
            ),
        },
        "git": {
            "run_as_user": run_as_user,
            "git_binary": _absolute_path(
                git.get("git_binary", "/usr/bin/git"), "git.git_binary"
            ),
            "repositories": repositories,
        },
        "policy": {
            "collection_warning_age_seconds": warning_age,
            "collection_critical_age_seconds": critical_age,
            "remote_sync_grace_seconds": _positive_int(
                policy.get("remote_sync_grace_seconds", 300),
                "policy.remote_sync_grace_seconds",
                minimum=0,
            ),
            "remote_verification_max_age_seconds": _positive_int(
                policy.get("remote_verification_max_age_seconds", 3600),
                "policy.remote_verification_max_age_seconds",
            ),
            "fsck_interval_seconds": _positive_int(
                policy.get("fsck_interval_seconds", 3600),
                "policy.fsck_interval_seconds",
                minimum=300,
            ),
            "orphan_state": orphan_state,
        },
    }
    return mode, interval, normalized


def config_lines(conf: object) -> list[str]:
    _mode, _interval, normalized = normalize_rule(conf)
    return json.dumps(normalized, indent=2, sort_keys=True).splitlines()


def hook_lines() -> list[str]:
    return [
        "hooks:",
        "  checkmk_oxidized_backup_state:",
        "    type: exec",
        "    events:",
        "      - node_success",
        "      - node_fail",
        "      - post_store",
        "    cmd: >-",
        f"      {HOOK_HELPER_PATH}",
        "      --record-hook",
        f"      --config {CONFIG_PATH}",
        "    timeout: 10",
        "    async: false",
    ]


def state_directories(conf: object) -> tuple[str, str, str]:
    _mode, _interval, normalized = normalize_rule(conf)
    hook_state = Path(normalized["state"]["hook_state_file"])
    monitor_state = Path(normalized["state"]["monitor_state_file"])
    return (
        str(hook_state.parent),
        str(monitor_state.parent),
        normalized["git"]["run_as_user"],
    )


def copied_config(conf: object) -> dict[str, Any]:
    """Return a defensive copy for tests and consumers that need a mapping."""

    _mode, _interval, normalized = normalize_rule(conf)
    return copy.deepcopy(normalized)
