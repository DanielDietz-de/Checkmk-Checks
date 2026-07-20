#!/usr/bin/env python3

"""AudioCodes HA module states, keepalive KPIs and synchronization alarms."""

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


_HA_ALARM_MARKERS = (
    "achasystemfaultalarm",
    "achasystemconfigmismatchalarm",
    "achasystemswitchoveralarm",
    "ha system fault",
    "ha configuration mismatch",
    "ha config mismatch",
    "ha switchover",
    "high availability",
    "redundant unit",
    "synchroniz",
    "not synchronized",
)

_OPERATIONAL_STATE = {
    "0": ("Invalid state", State.CRIT),
    "1": ("Disabled", State.CRIT),
    "2": ("Enabled", State.OK),
}

_PRESENCE = {
    "0": ("Invalid status", State.CRIT),
    "1": ("Present", State.OK),
    "2": ("Missing", State.CRIT),
}

# Same enum semantics as Checkmk's built-in AudioCodes operational-state check.
_HA_STATUS = {
    "0": ("Invalid status", State.CRIT),
    "1": ("Active - no HA", State.WARN),
    "2": ("Active", State.OK),
    "3": ("Redundant", State.OK),
    "4": ("Stand alone", State.OK),
    "5": ("Redundant - no HA", State.WARN),
    "6": ("Not applicable", State.OK),
}


def _to_percent(value):
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"", "null", "none", "nosuchinstance", "nosuchobject"}:
        return None
    try:
        # AudioCodes exposes HA packet loss in 0.01-percent units.
        return float(normalized) / 100.0
    except ValueError:
        return None


def _retained_max(rows, column):
    values = [_to_percent(row[column]) for row in rows if len(row) > column]
    valid_values = [value for value in values if value is not None]
    return max(valid_values) if valid_values else None


def _table(string_table, index):
    return string_table[index] if len(string_table) > index else []


def parse_acgateway_ha(string_table):
    current_table = _table(string_table, 0)
    history = _table(string_table, 1)
    module_rows = _table(string_table, 2)
    current = current_table[0] if current_table else []

    modules = []
    for row in module_rows:
        if len(row) < 4:
            continue
        modules.append(
            {
                "index": row[0],
                "operational_state": row[1],
                "presence": row[2],
                "ha_status": row[3],
            }
        )

    section = {
        "redundant_packet_loss": _to_percent(current[0]) if len(current) > 0 else None,
        "active_packet_loss": _to_percent(current[1]) if len(current) > 1 else None,
        "redundant_packet_loss_max": _retained_max(history, 1),
        "active_packet_loss_max": _retained_max(history, 2),
        "modules": modules,
    }

    has_kpi = any(
        section[key] is not None
        for key in (
            "redundant_packet_loss",
            "active_packet_loss",
            "redundant_packet_loss_max",
            "active_packet_loss_max",
        )
    )
    return section if has_kpi or modules else None


snmp_section_acgateway_ha = SNMPSection(
    name="acgateway_ha",
    parse_function=parse_acgateway_ha,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.5003.15.6.2.1.1",
            oids=[
                "1.0",  # acKpiHaStatsCurrentGlobalHaRedundantPacketLoss.0
                "2.0",  # acKpiHaStatsCurrentGlobalHaActivePacketLoss.0
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5003.15.6.2.2.1.1.1",
            oids=[
                OIDEnd(),
                "2",  # acKpiHaStatsIntervalGlobalHaRedundantPacketLossMax
                "4",  # acKpiHaStatsIntervalGlobalHaActivePacketLossMax
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5003.9.10.10.4.21.1",
            oids=[
                OIDEnd(),
                "8",  # acSysModuleOperationalState
                "4",  # acSysModulePresence
                "9",  # acSysModuleHAStatus
            ],
        ),
    ],
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5003.8.1.1"),
)


def _alarm_text(alarm):
    return " ".join(str(alarm.get(key, "")) for key in ("name", "desc", "source")).lower()


def _ha_alarms(section_acgateway_alarms):
    if not section_acgateway_alarms:
        return []
    return [
        alarm
        for alarm in section_acgateway_alarms.get("alarms", [])
        if any(marker in _alarm_text(alarm) for marker in _HA_ALARM_MARKERS)
    ]


def discover_acgateway_ha(section_acgateway_ha, section_acgateway_alarms):
    del section_acgateway_alarms
    if section_acgateway_ha:
        yield Service()


def _mapped_result(mapping, raw_value, label):
    name, state = mapping.get(raw_value, (f"Unknown ({raw_value})", State.UNKNOWN))
    return Result(state=state, notice=f"{label}: {name}")


def _yield_loss(section, key, label, metric_name):
    value = section.get(key)
    if value is None:
        return
    yield Result(state=State.OK, summary=f"{label}: {value:.2f}%")
    yield Metric(metric_name, value, boundaries=(0, 100))


def check_acgateway_ha(section_acgateway_ha, section_acgateway_alarms):
    modules = section_acgateway_ha.get("modules", [])
    if modules:
        ha_names = []
        for module in modules:
            ha_name, _ = _HA_STATUS.get(
                module["ha_status"],
                (f"Unknown ({module['ha_status']})", State.UNKNOWN),
            )
            ha_names.append(f"module {module['index']}: {ha_name}")

            yield _mapped_result(
                _OPERATIONAL_STATE,
                module["operational_state"],
                f"Module {module['index']} operational state",
            )
            yield _mapped_result(
                _PRESENCE,
                module["presence"],
                f"Module {module['index']} presence",
            )
            yield _mapped_result(
                _HA_STATUS,
                module["ha_status"],
                f"Module {module['index']} HA status",
            )

        yield Result(state=State.OK, summary="HA modules: " + ", ".join(ha_names))

    alarms = _ha_alarms(section_acgateway_alarms)
    if not alarms:
        yield Result(
            state=State.OK,
            summary="Synchronization: no active HA fault or configuration-mismatch alarm",
        )
    else:
        for alarm in alarms:
            yield Result(
                state=alarm.get("state", State.UNKNOWN),
                notice=f"{alarm.get('name', 'HA alarm')}: {alarm.get('desc', '')}",
            )

    yield from _yield_loss(
        section_acgateway_ha,
        "active_packet_loss",
        "Active-unit HA keepalive packet loss",
        "ha_active_packet_loss",
    )
    yield from _yield_loss(
        section_acgateway_ha,
        "redundant_packet_loss",
        "Redundant-unit HA keepalive packet loss",
        "ha_redundant_packet_loss",
    )
    yield from _yield_loss(
        section_acgateway_ha,
        "active_packet_loss_max",
        "Peak active-unit packet loss (retained hour)",
        "ha_active_packet_loss_max",
    )
    yield from _yield_loss(
        section_acgateway_ha,
        "redundant_packet_loss_max",
        "Peak redundant-unit packet loss (retained hour)",
        "ha_redundant_packet_loss_max",
    )


check_plugin_acgateway_ha = CheckPlugin(
    name="acgateway_ha",
    sections=["acgateway_ha", "acgateway_alarms"],
    service_name="SBC HA Health",
    discovery_function=discover_acgateway_ha,
    check_function=check_acgateway_ha,
)
