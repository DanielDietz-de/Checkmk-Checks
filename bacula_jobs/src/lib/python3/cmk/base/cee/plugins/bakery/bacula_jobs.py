#!/usr/bin/env python3
"""Modern Agent Bakery integration for the Bacula jobs collector."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .bakery_api.v1 import (
    FileGenerator,
    OS,
    Plugin,
    PluginConfig,
    register,
)

_DEPLOYMENT_MODES = {"sync", "cached", "do_not_deploy"}


def _normalize_deployment(value: Any) -> tuple[str, Any]:
    """Translate current choices and historical deploy/disable sentinels."""

    if value is None:
        return "do_not_deploy", None
    if isinstance(value, Mapping):
        # The historical deployment dropdown used an empty dictionary for
        # "deploy". Treat mapping values as synchronous deployment rather than
        # stringifying them or accidentally enabling a disabled rule.
        return "sync", None
    if isinstance(value, (tuple, list)) and value:
        mode = str(value[0])
        if mode in _DEPLOYMENT_MODES:
            interval = value[1] if len(value) > 1 else None
            return mode, interval
        return "do_not_deploy", None
    if isinstance(value, str) and value in _DEPLOYMENT_MODES:
        return value, None
    return "do_not_deploy", None


def _normalize(conf: Any) -> tuple[str, dict[str, Any]]:
    """Accept the new dictionary and the historical (deployment, config) tuple."""
    if isinstance(conf, Mapping):
        deployment = conf.get("deployment", ("cached", 300.0))
        settings = dict(conf.get("settings", {}))
    elif isinstance(conf, (tuple, list)) and len(conf) >= 2:
        deployment = conf[0]
        settings = dict(conf[1]) if isinstance(conf[1], Mapping) else {}
    else:
        deployment = None
        settings = {}

    mode, interval = _normalize_deployment(deployment)

    # Map historical field names without interpreting them as shell content.
    normalized = {
        "backend": "postgresql"
        if settings.get("backend_type") in {"pgsql", "postgresql"}
        else settings.get("backend", "mysql"),
        "database": settings.get("database", settings.get("dbname", "bacula")),
        "user": settings.get("user", settings.get("dbuser", "bacula")),
        "host": settings.get("host", settings.get("dbhost", "localhost")),
        "port": settings.get("port"),
        "timeout": settings.get("timeout", 15),
    }
    for key in (
        "mysql_defaults_file",
        "postgres_passfile",
        "postgres_os_user",
    ):
        if settings.get(key):
            normalized[key] = settings[key]
    normalized = {key: value for key, value in normalized.items() if value is not None}
    return mode, {"interval": interval, "settings": normalized}


def get_files(conf: Any) -> FileGenerator:
    mode, normalized = _normalize(conf)
    if mode == "do_not_deploy":
        return
    interval = None
    if mode == "cached":
        raw_interval = normalized["interval"]
        interval = int(float(raw_interval if raw_interval is not None else 300))

    yield Plugin(
        base_os=OS.LINUX,
        source=Path("bacula_jobs"),
        interval=interval,
    )
    yield PluginConfig(
        base_os=OS.LINUX,
        lines=json.dumps(
            normalized["settings"],
            indent=2,
            sort_keys=True,
        ).splitlines(),
        target=Path("bacula_jobs.json"),
    )


register.bakery_plugin(
    # Match the historical agent_config:bacula ruleset identifier.
    name="bacula",
    files_function=get_files,
)
