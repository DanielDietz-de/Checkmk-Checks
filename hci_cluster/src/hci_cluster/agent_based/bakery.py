#!/usr/bin/env python3
"""Agent bakery hook for HCI cluster monitoring."""

from pathlib import Path
from typing import Any

from cmk.base.cee.plugins.bakery.bakery_api.v1 import (
    FileGenerator,
    OS,
    Plugin,
    PluginConfig,
    register,
)


def _deployment_configuration(conf: Any) -> dict[str, Any] | None:
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
    return "'" + str(value).replace("'", "''") + "'"


def _get_lines(conf: dict[str, Any]) -> list[str]:
    return [
        f"$domain = {_powershell_literal(conf['domain'])}",
        f"$FilterTyp = {_powershell_literal(conf.get('filter_type', 'None'))}",
        f"$FilterPattern = {_powershell_literal(conf.get('filter_pattern', ''))}",
    ]


def get_hci_cluster_files(conf: Any) -> FileGenerator:
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
