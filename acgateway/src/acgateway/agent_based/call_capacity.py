#!/usr/bin/env python3

"""AudioCodes SBC call-capacity and peak-session monitoring."""

from cmk.agent_based.v2 import (
    CheckPlugin,
    Metric,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    contains,
)


def _to_int(value):
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"", "null", "none", "nosuchinstance", "nosuchobject"}:
        return None
    try:
        return int(normalized)
    except ValueError:
        return None


def _retained_max(rows, column):
    values = [_to_int(row[column]) for row in rows if len(row) > column]
    valid_values = [value for value in values if value is not None]
    return max(valid_values) if valid_values else None


def parse_acgateway_call_capacity(string_table):
    current_table = string_table[0] if string_table else []
    current = current_table[0] if current_table else []
    history = string_table[1] if len(string_table) > 1 else []

    section = {
        "active_calls_in": _to_int(current[0]) if len(current) > 0 else None,
        "active_calls_out": _to_int(current[1]) if len(current) > 1 else None,
        "active_sessions": _to_int(current[2]) if len(current) > 2 else None,
        # Each source value is already the maximum of one 15-minute interval.
        # Taking the maximum of the retained rows provides the peak over the
        # complete retention window (normally four intervals / one hour).
        "active_calls_in_max": _retained_max(history, 1),
        "active_calls_out_max": _retained_max(history, 2),
        "active_sessions_max": _retained_max(history, 3),
    }

    return section if any(value is not None for value in section.values()) else None


snmp_section_acgateway_call_capacity = SNMPSection(
    name="acgateway_call_capacity",
    parse_function=parse_acgateway_call_capacity,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.5003.15.3.1.1.1",
            oids=[
                "2.0",   # acKpiSbcCallStatsCurrentGlobalActiveCallsIn.0
                "3.0",   # acKpiSbcCallStatsCurrentGlobalActiveCallsOut.0
                "43.0",  # acKpiSbcCallStatsCurrentGlobalActiveSessions.0
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5003.15.3.1.2.1.1.1",
            oids=[
                OIDEnd(),
                "4",   # acKpiSbcCallStatsIntervalGlobalActiveCallsInMax
                "6",   # acKpiSbcCallStatsIntervalGlobalActiveCallsOutMax
                "50",  # acKpiSbcCallStatsIntervalGlobalActiveSessionsMax
            ],
        ),
    ],
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5003.8.1.1"),
)


def discover_acgateway_call_capacity(section):
    yield Service()


def _yield_value(section, key, label, metric_name):
    value = section.get(key)
    if value is None:
        return
    yield Result(state=State.OK, summary=f"{label}: {value}")
    yield Metric(metric_name, value, boundaries=(0, None))


def check_acgateway_call_capacity(section):
    yield from _yield_value(section, "active_calls_in", "Active calls in", "active_calls_in")
    yield from _yield_value(section, "active_calls_out", "Active calls out", "active_calls_out")
    yield from _yield_value(section, "active_sessions", "Active sessions", "active_sessions")
    yield from _yield_value(
        section,
        "active_calls_in_max",
        "Peak active calls in (retained hour)",
        "active_calls_in_max",
    )
    yield from _yield_value(
        section,
        "active_calls_out_max",
        "Peak active calls out (retained hour)",
        "active_calls_out_max",
    )
    yield from _yield_value(
        section,
        "active_sessions_max",
        "Peak active sessions (retained hour)",
        "active_sessions_max",
    )

    if section.get("active_sessions") is None and section.get("active_sessions_max") is None:
        yield Result(
            state=State.UNKNOWN,
            notice="Active Sessions KPI unavailable; enable SDR syslog or SDR local storage",
        )


check_plugin_acgateway_call_capacity = CheckPlugin(
    name="acgateway_call_capacity",
    service_name="SBC Call Capacity",
    discovery_function=discover_acgateway_call_capacity,
    check_function=check_acgateway_call_capacity,
)
