#!/usr/bin/env python3

"""AudioCodes SIP TLS connection statistics and certificate alarms."""

from time import time

from cmk.agent_based.v2 import (
    CheckPlugin,
    GetRateError,
    Metric,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    contains,
    get_rate,
    get_value_store,
)


_TLS_ALARM_MARKERS = (
    "accertificateexpiryalarm",
    "actlssocketslimitalarm",
    "tls",
    "certificate expir",
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


def parse_acgateway_tls(string_table):
    current_table = string_table[0] if string_table else []
    current = current_table[0] if current_table else []
    history = string_table[1] if len(string_table) > 1 else []

    section = {
        "attempted_total": _to_int(current[0]) if len(current) > 0 else None,
        "rejected_total": _to_int(current[1]) if len(current) > 1 else None,
        "active_connections": _to_int(current[2]) if len(current) > 2 else None,
        # TLS history retains up to 100 intervals (25 hours).
        "active_connections_max": _retained_max(history, 2),
        "rejected_connections_max": _retained_max(history, 3),
        "attempted_connections_max": _retained_max(history, 4),
    }

    return section if any(value is not None for value in section.values()) else None


snmp_section_acgateway_tls = SNMPSection(
    name="acgateway_tls",
    parse_function=parse_acgateway_tls,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.5003.15.6.4.1.2",
            oids=[
                "1.0",  # acKpiTlsStatsCurrentGlobalAttemptedSipTlsConnTotal.0
                "2.0",  # acKpiTlsStatsCurrentGlobalRejectedSipTlsConnTotal.0
                "3.0",  # acKpiTlsStatsCurrentGlobalActiveSipTlsConn.0
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5003.15.6.4.2.1.2.1",
            oids=[
                OIDEnd(),
                "2",  # acKpiTlsStatsIntervalGlobalActiveSipTlsConnAvg
                "3",  # acKpiTlsStatsIntervalGlobalActiveSipTlsConnMax
                "4",  # acKpiTlsStatsIntervalGlobalRejectedSipTlsConn
                "5",  # acKpiTlsStatsIntervalGlobalAttemptedSipTlsConn
            ],
        ),
    ],
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5003.8.1.1"),
)


def _alarm_text(alarm):
    return " ".join(
        str(alarm.get(key, "")) for key in ("name", "desc", "source")
    ).lower()


def _tls_alarms(section_acgateway_alarms):
    if not section_acgateway_alarms:
        return []
    return [
        alarm
        for alarm in section_acgateway_alarms.get("alarms", [])
        if any(marker in _alarm_text(alarm) for marker in _TLS_ALARM_MARKERS)
    ]


def discover_acgateway_tls(section_acgateway_tls, section_acgateway_alarms):
    del section_acgateway_alarms
    if section_acgateway_tls:
        yield Service()


def check_acgateway_tls(section_acgateway_tls, section_acgateway_alarms):
    alarms = _tls_alarms(section_acgateway_alarms)
    if not alarms:
        yield Result(
            state=State.OK,
            summary="No active TLS connection-limit or certificate-expiry alarms",
        )
    else:
        for alarm in alarms:
            yield Result(
                state=alarm.get("state", State.UNKNOWN),
                notice=f"{alarm.get('name', 'TLS alarm')}: {alarm.get('desc', '')}",
            )

    active = section_acgateway_tls.get("active_connections")
    if active is not None:
        yield Result(state=State.OK, summary=f"Active SIP TLS connections: {active}")
        yield Metric("active_tls_connections", active, boundaries=(0, None))

    active_max = section_acgateway_tls.get("active_connections_max")
    if active_max is not None:
        yield Result(
            state=State.OK,
            summary=f"Peak SIP TLS connections (retained 25h): {active_max}",
        )
        yield Metric("active_tls_connections_max", active_max, boundaries=(0, None))

    for key, label, metric_name in (
        (
            "attempted_connections_max",
            "Most attempted TLS connections in one interval",
            "attempted_tls_connections_max",
        ),
        (
            "rejected_connections_max",
            "Most rejected TLS connections in one interval",
            "rejected_tls_connections_max",
        ),
    ):
        value = section_acgateway_tls.get(key)
        if value is not None:
            yield Result(state=State.OK, summary=f"{label}: {value}")
            yield Metric(metric_name, value, boundaries=(0, None))

    value_store = get_value_store()
    now = time()
    for key, label, metric_name in (
        ("attempted_total", "TLS connection attempts", "tls_connection_attempts_per_sec"),
        ("rejected_total", "Rejected TLS connections", "tls_rejected_connections_per_sec"),
    ):
        total = section_acgateway_tls.get(key)
        if total is None:
            continue
        try:
            rate = get_rate(value_store, f"acgateway_tls.{key}", now, total)
        except GetRateError:
            continue
        yield Result(state=State.OK, summary=f"{label}: {rate:.3f}/s")
        yield Metric(metric_name, rate, boundaries=(0, None))


check_plugin_acgateway_tls = CheckPlugin(
    name="acgateway_tls",
    sections=["acgateway_tls", "acgateway_alarms"],
    service_name="SBC TLS Health",
    discovery_function=discover_acgateway_tls,
    check_function=check_acgateway_tls,
)
