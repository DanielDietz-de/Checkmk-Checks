#!/usr/bin/env python3
"""SNMP check for Sidecooler warm- and cold-side temperatures."""

from cmk.agent_based.v2 import (
    CheckPlugin,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    exists,
)


class SidecoolerTemp:
    def __init__(self, warm: dict[str, float], cold: dict[str, float]) -> None:
        self.warm = warm
        self.cold = cold


def parse_sidecooler_temp(string_table):
    if not string_table:
        return None

    values = [int(value) / 10 for value in string_table[0]]
    warm = dict(zip(("mean", "top", "center", "bottom"), values[:4], strict=True))
    cold = dict(zip(("mean", "top", "center", "bottom"), values[4:8], strict=True))
    return SidecoolerTemp(warm, cold)


def discover_sidecooler_temp(section):
    if section.warm:
        yield Service(item="warm")
    if section.cold:
        yield Service(item="cold")


def check_sidecooler_temp(item, params, section):
    data = section.warm if item == "warm" else section.cold
    metric_prefix = "temp_warm_" if item == "warm" else "temp_cold_"

    for which in ("mean", "top", "center", "bottom"):
        value = data[which]
        levels = params[which]
        if levels[0] == "no_levels":
            yield Result(state=State.OK, summary=f"{which.capitalize()}: {value}°C")
            yield Metric(name=f"{metric_prefix}{which}", value=value)
            continue

        warn, crit = levels[1]
        if value >= crit:
            state = State.CRIT
        elif value >= warn:
            state = State.WARN
        else:
            state = State.OK
        yield Result(state=state, summary=f"{which.capitalize()}: {value}°C")
        yield Metric(name=f"{metric_prefix}{which}", value=value, levels=levels[1])


snmp_section_sidecooler_temp = SimpleSNMPSection(
    name="sidecooler_temp",
    parse_function=parse_sidecooler_temp,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.46984.17.3",
        oids=[
            "1", "2", "3", "4",  # Warm mean, top, center, bottom
            "5", "6", "7", "8",  # Cold mean, top, center, bottom
        ],
    ),
    detect=exists(".1.3.6.1.4.1.46984.17.3.*"),
)


check_plugin_sidecooler_temp = CheckPlugin(
    name="sidecooler_temp",
    service_name="Sidecooler Temp %s side",
    discovery_function=discover_sidecooler_temp,
    check_function=check_sidecooler_temp,
    check_ruleset_name="sidecooler_temp",
    check_default_parameters={
        "mean": ("fixed", (30.0, 35.0)),
        "top": ("fixed", (30.0, 35.0)),
        "center": ("fixed", (30.0, 35.0)),
        "bottom": ("fixed", (30.0, 35.0)),
    },
)
