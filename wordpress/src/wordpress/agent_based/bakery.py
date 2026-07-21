#!/usr/bin/env python3

from pathlib import Path
from typing import Any

from cmk.base.cee.plugins.bakery.bakery_api.v1 import (
    FileGenerator,
    OS,
    Plugin,
    PluginConfig,
    register,
)


def _get_config(conf: dict[str, Any]) -> list[str]:
    base_dir = str(conf.get("base_dir", "/var/www/sites.d"))
    search_string = str(conf.get("search_string", "deploy/current"))
    return [
        f"BASEDIR={base_dir}",
        f"SEARCH_STRING={search_string}",
    ]


def get_files(conf: dict[str, Any]) -> FileGenerator:
    mode = conf.get("deployment", ("do_not_deploy", None))
    match mode:
        case ("do_not_deploy", _):
            return
        case ("cached", raw_interval):
            interval: int | None = int(float(raw_interval))
        case ("sync", _):
            interval = None
        case _:
            return

    yield Plugin(
        base_os=OS.LINUX,
        source=Path("wp_instances.php"),
        interval=interval,
    )
    yield PluginConfig(
        base_os=OS.LINUX,
        lines=_get_config(conf),
        target=Path("wp_instances.cfg"),
    )


register.bakery_plugin(
    name="wordpress_instances",
    files_function=get_files,
)
