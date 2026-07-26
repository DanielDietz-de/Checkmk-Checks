#!/usr/bin/env python3
"""Checkmk Agent Bakery integration for oxidized_backup."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cmk_addons.plugins.oxidized_backup.bakery_common import (
    HOOK_HELPER_PATH,
    config_lines,
    hook_lines,
    normalize_rule,
    state_directories,
)

from .bakery_api.v1 import (
    DebStep,
    FileGenerator,
    OS,
    Plugin,
    PluginConfig,
    RpmStep,
    Scriptlet,
    ScriptletGenerator,
    SystemBinary,
    SystemConfig,
    quote_shell_string,
    register,
)


def get_files(conf: Any) -> FileGenerator:
    mode, interval, _normalized = normalize_rule(conf)
    if mode == "do_not_deploy":
        return

    yield Plugin(
        base_os=OS.LINUX,
        source=Path("oxidized_backup"),
        target=Path("oxidized_backup"),
        interval=interval,
    )
    yield SystemBinary(
        base_os=OS.LINUX,
        source=Path("plugins/oxidized_backup"),
        target=Path(Path(HOOK_HELPER_PATH).name),
    )
    yield PluginConfig(
        base_os=OS.LINUX,
        lines=config_lines(conf),
        target=Path("oxidized_backup.json"),
        include_header=False,
    )
    yield SystemConfig(
        base_os=OS.LINUX,
        lines=hook_lines(),
        target=Path("check_mk/oxidized_backup-hook.yml"),
        include_header=True,
    )


def get_scriptlets(conf: Any, aghash: str) -> ScriptletGenerator:
    del aghash
    mode, _interval, _normalized = normalize_rule(conf)
    if mode == "do_not_deploy":
        return

    hook_directory, monitor_directory, run_as_user = state_directories(conf)
    quoted_hook_directory = quote_shell_string(hook_directory)
    quoted_monitor_directory = quote_shell_string(monitor_directory)
    quoted_user = quote_shell_string(run_as_user)

    lines = [
        f"install -d -m 0700 -o root -g root {quoted_monitor_directory}",
        f"if getent passwd {quoted_user} >/dev/null 2>&1; then",
        f"    oxidized_backup_group=$(id -gn {quoted_user})",
        (
            f"    install -d -m 0750 -o {quoted_user} "
            f"-g \"$oxidized_backup_group\" {quoted_hook_directory}"
        ),
        "else",
        (
            "    printf '%s\\n' "
            f"'oxidized_backup: user {run_as_user} does not exist; "
            "hook state directory was not created' >&2"
        ),
        "fi",
    ]
    yield Scriptlet(step=DebStep.POSTINST, lines=lines)
    yield Scriptlet(step=RpmStep.POST, lines=lines)


register.bakery_plugin(
    name="oxidized_backup",
    files_function=get_files,
    scriptlets_function=get_scriptlets,
)
