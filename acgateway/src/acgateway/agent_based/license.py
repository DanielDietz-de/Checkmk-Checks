#!/usr/bin/env python3

"""AudioCodes SBC media/signaling license utilization and idle headroom."""

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


def _to_float(value):
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"", "null", "none", "nosuchinstance", "nosuchobject"}:
        return None
    try:
        return float(normalized)
    except ValueError:
        return None


def _retained_max(rows, column):
    values = [_to_float(row[column]) for row in rows if len(row) > column]
    valid_values = [value for value in values if value is not None]
    return max(valid_values) if valid_values else None


def _headroom(*values):
    valid_values = [value for value in values if value is not None]
    if not valid_values:
        return None
    return max(0.0, 100.0 - max(valid_values))


def parse_acgateway_license(string_table):
    current_table = string_table[0] if string_table else []
    current = current_table[0] if current_table else []
    history = string_table[1] if len(string_table) > 1 else []

    media_usage = _to_float(current[0]) if len(current) > 0 else None
    signaling_usage = _to_float(current[1]) if len(current) > 1 else None
    media_usage_max = _retained_max(history, 1)
    signaling_usage_max = _retained_max(history, 2)

    section = {
        "media_usage": media_usage,
        "signaling_usage": signaling_usage,
        "media_usage_max": media_usage_max,
        "signaling_usage_max": signaling_usage_max,
        # AudioCodes has no KPI named "Idles of". The useful equivalent is
        # remaining licensed capacity. It is intentionally reported as a
        # percentage because the licensed absolute session count is not part
        # of these KPI objects.
        "idle_capacity": _headroom(media_usage, signaling_usage),
        "idle_capacity_min": _headroom(media_usage_max, signaling_usage_max),
    }

    return section if any(value is not None for value in section.values()) else None


snmp_section_acgateway_license = SNMPSection(
    name="acgateway_license",
    parse_function=parse_acgateway_license,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.5003.15.2.1.1.1",
            oids=[
                "3.0",  # acKpiLicenseStatsCurrentGlobalLicenseSbcMediaUsage.0
                "4.0",  # acKpiLicenseStatsCurrentGlobalLicenseSbcSignalingUsage.0
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5003.15.2.1.2.1.1.1",
            oids=[
                OIDEnd(),
                "6",  # acKpiLicenseStatsIntervalGlobalLicenseSbcMediaUsageMax
                "8",  # acKpiLicenseStatsIntervalGlobalLicenseSbcSignalingUsageMax
            ],
        ),
    ],
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5003.8.1.1"),
)


def discover_acgateway_license(section):
    yield Service()


def _yield_percent(section, key, label, metric_name):
    value = section.get(key)
    if value is None:
        return
    yield Result(state=State.OK, summary=f"{label}: {value:.1f}%")
    yield Metric(metric_name, value, boundaries=(0, 100))


def check_acgateway_license(section):
    yield from _yield_percent(section, "media_usage", "SBC media usage", "sbc_media_license_usage")
    yield from _yield_percent(
        section,
        "signaling_usage",
        "SBC signaling usage",
        "sbc_signaling_license_usage",
    )
    yield from _yield_percent(
        section,
        "media_usage_max",
        "Peak SBC media usage (retained hour)",
        "sbc_media_license_usage_max",
    )
    yield from _yield_percent(
        section,
        "signaling_usage_max",
        "Peak SBC signaling usage (retained hour)",
        "sbc_signaling_license_usage_max",
    )
    yield from _yield_percent(
        section,
        "idle_capacity",
        "Idle licensed capacity",
        "sbc_license_idle_capacity",
    )
    yield from _yield_percent(
        section,
        "idle_capacity_min",
        "Minimum idle capacity (retained hour)",
        "sbc_license_idle_capacity_min",
    )


check_plugin_acgateway_license = CheckPlugin(
    name="acgateway_license",
    service_name="SBC License Usage",
    discovery_function=discover_acgateway_license,
    check_function=check_acgateway_license,
)
