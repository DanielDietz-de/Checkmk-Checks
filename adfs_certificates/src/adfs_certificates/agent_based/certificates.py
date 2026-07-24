#!/usr/bin/env python3
"""
ADFS Certificate Check Plugin

Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""
import json

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Result,
    Service,
    State,
    check_levels,
)


def parse_adfs_certificates(string_table):
    parsed = {}
    for line in string_table:
        try:
            data = json.loads(line[0])
            if "error" in data:
                parsed["_error"] = data["error"]
            else:
                parsed[data["item"]] = data
        except (json.JSONDecodeError, KeyError):
            continue
    return parsed


agent_section_adfs_certificates = AgentSection(
    name="adfs_certificates",
    parse_function=parse_adfs_certificates,
)


def discover_adfs_certificates(section):
    for item in section:
        if item != "_error":
            yield Service(item=item)


def check_adfs_certificates(item, params, section):
    if "_error" in section and item not in section:
        yield Result(state=State.CRIT, summary=f"Agent error: {section['_error']}")
        return

    data = section.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary=f"No data for {item}")
        return

    days = data["days_remaining"]
    subject = data.get("subject", "unknown")
    not_after = data.get("not_after", "unknown")

    warn_days = params.get("warn_days", 30)
    crit_days = params.get("crit_days", 14)

    yield from check_levels(
        days,
        metric_name="certificate_validity_days",
        levels_lower=("fixed", (warn_days, crit_days)),
        label="Days remaining",
        render_func=lambda v: f"{int(v)} days",
    )

    yield Result(
        state=State.OK,
        notice=f"Subject: {subject}, Expires: {not_after}",
    )


check_plugin_adfs_certificates = CheckPlugin(
    name="adfs_certificates",
    service_name="ADFS Certificate %s",
    discovery_function=discover_adfs_certificates,
    check_function=check_adfs_certificates,
    check_ruleset_name="adfs_certificates",
    check_default_parameters={"warn_days": 30, "crit_days": 14},
)
