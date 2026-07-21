#!/usr/bin/env python3

import itertools
import json
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Any]


def parse_wp_instances(string_table: StringTable) -> Section:
    text = "".join(itertools.chain.from_iterable(string_table))
    if not text:
        return {"instances": [], "error": "WordPress agent returned an empty section"}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"instances": [], "error": f"Invalid JSON from WordPress agent: {exc}"}
    if not isinstance(payload, dict):
        return {"instances": [], "error": "WordPress agent payload is not a JSON object"}
    instances = payload.get("instances", [])
    if not isinstance(instances, list):
        return {**payload, "instances": [], "error": "WordPress instances are not a list"}
    return payload


def discover_wp_instances(section: Section):
    for instance in section.get("instances", []):
        if isinstance(instance, Mapping):
            name = instance.get("name")
            if isinstance(name, str) and name:
                yield Service(item=name)


def check_wp_instances(item: str, section: Section):
    for instance in section.get("instances", []):
        if not isinstance(instance, Mapping) or instance.get("name") != item:
            continue

        status = instance.get("core_status", 3)
        try:
            status_id = int(status)
        except (TypeError, ValueError):
            status_id = 3

        installed = str(instance.get("core_version") or "unknown")
        available = str(instance.get("core_new_version") or "unknown")
        error = instance.get("error")

        yield Metric("core_status", status_id, boundaries=(0, 3))
        if status_id == 0:
            yield Result(
                state=State.OK,
                summary=f"WordPress core {installed} is current",
            )
        elif status_id == 1:
            yield Result(
                state=State.WARN,
                summary=f"Patch update available: {installed} -> {available}",
            )
        elif status_id == 2:
            yield Result(
                state=State.CRIT,
                summary=f"Major or minor update available: {installed} -> {available}",
            )
        else:
            summary = str(error) if error else "Unable to determine WordPress core update status"
            yield Result(state=State.UNKNOWN, summary=summary)
        return

    yield Result(state=State.UNKNOWN, summary="WordPress instance data is missing")


agent_section_wordpress_instances = AgentSection(
    name="wordpress_instances",
    parse_function=parse_wp_instances,
)

check_plugin_wordpress_instances = CheckPlugin(
    name="wordpress_instances",
    service_name="Wordpress Core %s",
    sections=["wordpress_instances"],
    discovery_function=discover_wp_instances,
    check_function=check_wp_instances,
)
