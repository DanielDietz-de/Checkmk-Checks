#!/usr/bin/env python3
"""Agent bakery hook for HCI cluster monitoring."""

from pathlib import Path
from typing import Any

from .bakery_api.v1 import (
    FileGenerator,
    OS,
    Plugin,
    PluginConfig,
    register,
)

_FILTER_TYPE_TO_AGENT = {
    "none": "None",
    "inclusion": "Inclusion",
    "exclusion": "Exclusion",
    "None": "None",
    "Inclusion": "Inclusion",
    "Exclusion": "Exclusion",
}


def _deployment_configuration(conf: Any) -> dict[str, Any] | None:
    """Handle deployment configuration for this module's workflow."""
    if not isinstance(conf, dict):
        return None

    deployment = conf.get("deployment")
    if isinstance(deployment, tuple) and len(deployment) == 2:
        mode, parameters = deployment
        if mode != "deploy" or not isinstance(parameters, dict):
            return None
        return parameters

    # Preserve rules saved by the legacy WATO rulespec during migration.
    if "domain" in conf:
        return conf
    return None


def _powershell_literal(value: Any) -> str:
    """Handle powershell literal for this module's workflow."""
    return "'" + str(value).replace("'", "''") + "'"


def _filter_type_for_agent(value: Any) -> str:
    """Handle filter type for agent for this module's workflow."""
    return _FILTER_TYPE_TO_AGENT.get(str(value), "None")


def _get_lines(conf: dict[str, Any]) -> list[str]:
    """Handle get lines for this module's workflow."""
    return [
        f"$domain = {_powershell_literal(conf['domain'])}",
        f"$FilterTyp = {_powershell_literal(_filter_type_for_agent(conf.get('filter_type', 'none')))}",
        f"$FilterPattern = {_powershell_literal(conf.get('filter_pattern', ''))}",
    ]


def get_hci_cluster_files(conf: Any) -> FileGenerator:
    """Return hci cluster files for the supplied inputs."""
    parameters = _deployment_configuration(conf)
    if parameters is None:
        return

    yield Plugin(
        base_os=OS.WINDOWS,
        source=Path("hci_cluster.ps1"),
    )
    yield PluginConfig(
        base_os=OS.WINDOWS,
        lines=_get_lines(parameters),
        target=Path("hci_cluster.cfg.ps1"),
    )


register.bakery_plugin(
    name="hci_cluster",
    files_function=get_hci_cluster_files,
)
