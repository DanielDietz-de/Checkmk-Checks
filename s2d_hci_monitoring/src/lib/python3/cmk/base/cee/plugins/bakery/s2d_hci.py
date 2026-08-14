#!/usr/bin/env python3
"""Agent Bakery integration for bounded S2D/HCI Windows collectors."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .bakery_api.v1 import OS, Plugin, PluginConfig, SystemBinary, register

_DEFAULTS: dict[str, object] = {
    "fast_enabled": True,
    "storage_enabled": True,
    "jobs_enabled": True,
    "health_enabled": True,
    "virtualization_mode": "disabled",
    "max_records": 2000,
    "max_output_bytes": 1048576,
    "max_runtime_seconds": 120,
    "include_addresses": False,
    "include_paths": False,
    "include_serials": False,
    "include_locations": False,
}


def _strict_bool(value: object, default: bool) -> bool:
    """Normalize only explicit Boolean-compatible values and otherwise use a safe default."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return default


def _bounded_int(value: object, default: int, minimum: int, maximum: int) -> int:
    """Normalize an integer setting and clamp invalid input to the reviewed default."""

    try:
        converted = int(value)
    except (TypeError, ValueError):
        return default
    return converted if minimum <= converted <= maximum else default


def _normalize(conf: Any) -> dict[str, object]:
    """Return a complete fail-safe Bakery configuration from a mapping-like rule value."""

    source: Mapping[str, object] = conf if isinstance(conf, Mapping) else {}
    normalized = dict(_DEFAULTS)
    for key in (
        "fast_enabled",
        "storage_enabled",
        "jobs_enabled",
        "health_enabled",
        "include_addresses",
        "include_paths",
        "include_serials",
        "include_locations",
    ):
        normalized[key] = _strict_bool(source.get(key), bool(_DEFAULTS[key]))
    mode = str(source.get("virtualization_mode") or "disabled").strip().lower()
    normalized["virtualization_mode"] = mode if mode in {"disabled", "direct", "gmsa_spool"} else "disabled"
    normalized["max_records"] = _bounded_int(source.get("max_records"), 2000, 1, 5000)
    normalized["max_output_bytes"] = _bounded_int(source.get("max_output_bytes"), 1048576, 16384, 4194304)
    normalized["max_runtime_seconds"] = _bounded_int(source.get("max_runtime_seconds"), 120, 5, 240)
    return normalized


def get_files(conf: Any):
    """Yield Windows agent artifacts selected by the Bakery rule and bounded timeouts."""

    config = _normalize(conf)
    timeout = int(config["max_runtime_seconds"])

    # All direct collectors import the shared module from the Windows agent bin directory.
    yield SystemBinary(base_os=OS.WINDOWS, source=Path("bin/s2d_hci_common.psm1"), target=Path("s2d_hci_common.psm1"))

    collector_specs = (
        ("fast_enabled", "s2d_hci_fast.ps1", 120),
        ("storage_enabled", "s2d_hci_storage.ps1", 300),
        ("jobs_enabled", "s2d_hci_jobs.ps1", 300),
        ("health_enabled", "s2d_hci_health.ps1", 600),
    )
    for key, filename, interval in collector_specs:
        if config[key]:
            yield Plugin(
                base_os=OS.WINDOWS,
                source=Path(filename),
                interval=interval,
                timeout=timeout,
            )

    if config["virtualization_mode"] == "direct":
        yield Plugin(
            base_os=OS.WINDOWS,
            source=Path("s2d_hci_virtualization.ps1"),
            interval=300,
            timeout=timeout,
        )

    if config["virtualization_mode"] == "gmsa_spool":
        yield SystemBinary(
            base_os=OS.WINDOWS,
            source=Path("plugins/s2d_hci_virtualization.ps1"),
            target=Path("s2d_hci_virtualization.ps1"),
        )
        yield SystemBinary(
            base_os=OS.WINDOWS,
            source=Path("scripts/s2d_hci_virtualization_spool.ps1"),
            target=Path("s2d_hci_virtualization_spool.ps1"),
        )

    collector_config = {
        "protocol_version": 1,
        "max_records": config["max_records"],
        "max_output_bytes": config["max_output_bytes"],
        "max_runtime_seconds": config["max_runtime_seconds"],
        "include_addresses": config["include_addresses"],
        "include_paths": config["include_paths"],
        "include_serials": config["include_serials"],
        "include_locations": config["include_locations"],
        "virtualization_enabled": config["virtualization_mode"] != "disabled",
    }
    yield PluginConfig(
        base_os=OS.WINDOWS,
        lines=json.dumps(collector_config, indent=2, sort_keys=True).splitlines(),
        target=Path("s2d_hci.json"),
    )


register.bakery_plugin(name="s2d_hci", files_function=get_files)
