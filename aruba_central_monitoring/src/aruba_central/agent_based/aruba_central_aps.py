"""Checkmk Check API V2 plug-ins for Aruba Central access-point monitoring."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
import re
from typing import Any

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Metric, Result, Service, State, check_levels


@dataclass(frozen=True)
class Collector:
    """Represent collector behavior and associated state."""
    status: str
    message: str
    generated_at: str
    stale: bool
    last_success_age_seconds: int | None
    refresh_duration_seconds: float | None
    json_stream: str
    counts_stream: str
    rate_limit_stream: str
    ap_total: int
    ap_up: int
    ap_down: int
    clients_total: int
    api_rate_remaining: int | None
    api_rate_limit: int | None


@dataclass(frozen=True)
class Radio:
    """Represent radio behavior and associated state."""
    key: str
    index: int
    name: str
    radio_type: str
    band: str
    channel: str
    status: str
    tx_power: float | None
    utilization: float | None
    spatial_stream: str
    macaddr: str


@dataclass(frozen=True)
class AccessPoint:
    """Represent accesspoint behavior and associated state."""
    host_name: str
    name: str
    status: str
    device_type: str
    model: str
    clients: int
    ip_address: str
    mac: str
    serial: str
    group: str
    site: str
    uptime: str
    uptime_seconds: int | None
    cpu_percent: float | None
    mem_total_mb: float | None
    mem_free_mb: float | None
    version: str
    ssid_count: int | None
    sleep_status: bool
    radios: Mapping[str, Radio]


@dataclass(frozen=True)
class Section:
    """Represent section behavior and associated state."""
    kind: str
    collector: Collector | None
    access_point: AccessPoint | None


def _optional_int(value: Any) -> int | None:
    """Handle optional int for this module's workflow."""
    if value in (None, ""):
        return None
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    """Handle optional float for this module's workflow."""
    if value in (None, ""):
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _mapping(value: Any) -> Mapping[str, Any]:
    """Handle mapping for this module's workflow."""
    return value if isinstance(value, Mapping) else {}


def _collector(raw: Any) -> Collector | None:
    """Handle collector for this module's workflow."""
    data = _mapping(raw)
    if not data:
        return None
    return Collector(
        status=str(data.get("status", "UNKNOWN")),
        message=str(data.get("message", "")),
        generated_at=str(data.get("generated_at", "")),
        stale=bool(data.get("stale", False)),
        last_success_age_seconds=_optional_int(data.get("last_success_age_seconds")),
        refresh_duration_seconds=_optional_float(data.get("refresh_duration_seconds")),
        json_stream=str(data.get("json_stream", "unknown")),
        counts_stream=str(data.get("counts_stream", "unknown")),
        rate_limit_stream=str(data.get("rate_limit_stream", "unknown")),
        ap_total=_optional_int(data.get("ap_total")) or 0,
        ap_up=_optional_int(data.get("ap_up")) or 0,
        ap_down=_optional_int(data.get("ap_down")) or 0,
        clients_total=_optional_int(data.get("clients_total")) or 0,
        api_rate_remaining=_optional_int(data.get("api_rate_remaining")),
        api_rate_limit=_optional_int(data.get("api_rate_limit")),
    )


def _access_point(raw: Any) -> AccessPoint | None:
    """Handle access point for this module's workflow."""
    data = _mapping(raw)
    if not data:
        return None
    radios: dict[str, Radio] = {}
    raw_radios = data.get("radios")
    if isinstance(raw_radios, Sequence) and not isinstance(raw_radios, (str, bytes)):
        for index, raw_radio in enumerate(raw_radios):
            radio_data = _mapping(raw_radio)
            name = str(radio_data.get("radio_name", f"Radio {index}"))
            radio_index = _optional_int(radio_data.get("index"))
            if radio_index is None:
                radio_index = index
            normalized_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "radio"
            base_key = f"{normalized_name}_{radio_index}"
            key = base_key
            discriminator = index
            while key in radios:
                # Preserve every radio even if the source violates the expected unique
                # index contract or a fallback key collides with another natural key.
                # Enumeration order makes the discriminator deterministic for this payload.
                key = f"{base_key}_{discriminator}"
                discriminator += 1
            radios[key] = Radio(
                key=key,
                index=radio_index,
                name=name,
                radio_type=str(radio_data.get("radio_type", "")),
                band=str(radio_data.get("band", "")),
                channel=str(radio_data.get("channel", "")),
                status=str(radio_data.get("status", "Unknown")),
                tx_power=_optional_float(radio_data.get("tx_power")),
                utilization=_optional_float(radio_data.get("utilization")),
                spatial_stream=str(radio_data.get("spatial_stream", "")),
                macaddr=str(radio_data.get("macaddr", "")),
            )
    return AccessPoint(
        host_name=str(data.get("host_name", "")),
        name=str(data.get("name", "")),
        status=str(data.get("status", "Unknown")),
        device_type=str(data.get("type", "ap")),
        model=str(data.get("model", "")),
        clients=_optional_int(data.get("clients")) or 0,
        ip_address=str(data.get("ip", "")),
        mac=str(data.get("mac", "")),
        serial=str(data.get("serial", "")),
        group=str(data.get("group", "Unassigned")),
        site=str(data.get("site", "Unassigned")),
        uptime=str(data.get("uptime", "")),
        uptime_seconds=_optional_int(data.get("uptime_seconds")),
        cpu_percent=_optional_float(data.get("cpu_percent")),
        mem_total_mb=_optional_float(data.get("mem_total_mb")),
        mem_free_mb=_optional_float(data.get("mem_free_mb")),
        version=str(data.get("version", "")),
        ssid_count=_optional_int(data.get("ssid_count")),
        sleep_status=bool(data.get("sleep_status", False)),
        radios=radios,
    )


def parse_aruba_central_aps(string_table: Sequence[Sequence[str]]) -> Section:
    """Parse the single compressed JSON document emitted by the collector."""
    payload = "\n".join(row[0] for row in string_table if row)
    try:
        root = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return Section(kind="invalid", collector=None, access_point=None)
    if not isinstance(root, Mapping) or root.get("schema") != 1:
        return Section(kind="invalid", collector=None, access_point=None)
    kind = str(root.get("kind", "invalid"))
    return Section(
        kind=kind,
        collector=_collector(root.get("collector")),
        access_point=_access_point(root.get("ap")) if kind == "ap" else None,
    )


agent_section_aruba_central_aps = AgentSection(
    name="aruba_central_aps",
    parse_function=parse_aruba_central_aps,
)


def _state(value: object, default: int) -> State:
    """Handle state for this module's workflow."""
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        numeric = default
    return {0: State.OK, 1: State.WARN, 2: State.CRIT, 3: State.UNKNOWN}.get(numeric, State.UNKNOWN)


def _ratio(part: float | None, total: float | None) -> float | None:
    """Handle ratio for this module's workflow."""
    if part is None or total is None or total <= 0:
        return None
    return part * 100.0 / total


def discover_summary(section: Section):
    """Discover summary from the available input data."""
    if section.kind == "collector" and section.collector is not None:
        yield Service()


def check_summary(params: Mapping[str, object], section: Section):
    """Evaluate summary and return its resulting state."""
    collector = section.collector
    if collector is None:
        yield Result(state=State.UNKNOWN, summary="No valid Aruba Central collector data")
        return

    if collector.status.upper() != "OK":
        yield Result(state=State.CRIT, summary=collector.message or "Aruba Central collection failed")
    else:
        yield Result(
            state=State.OK,
            summary=f"{collector.ap_up}/{collector.ap_total} APs Up, {collector.clients_total} clients",
            details=(
                f"JSON stream: {collector.json_stream}\n"
                f"Counts stream: {collector.counts_stream}\n"
                f"Rate-limit stream: {collector.rate_limit_stream}\n"
                f"Generated at: {collector.generated_at}\n{collector.message}"
            ),
        )

    yield Metric("aruba_ap_total", float(collector.ap_total))
    yield Metric("aruba_ap_up", float(collector.ap_up))
    yield Metric("aruba_ap_down", float(collector.ap_down))
    yield Metric("aruba_clients_total", float(collector.clients_total))

    if collector.api_rate_remaining is not None:
        yield from check_levels(
            float(collector.api_rate_remaining),
            levels_lower=params.get("api_rate_remaining_lower", ("fixed", (500.0, 100.0))),
            metric_name="aruba_api_rate_remaining",
            label="API calls remaining",
            boundaries=(0.0, float(collector.api_rate_limit) if collector.api_rate_limit else None),
        )
    if collector.api_rate_limit is not None:
        yield Metric("aruba_api_rate_limit", float(collector.api_rate_limit))
    if collector.last_success_age_seconds is not None:
        yield from check_levels(
            float(collector.last_success_age_seconds),
            levels_upper=params.get("last_success_age_upper", ("fixed", (600.0, 1800.0))),
            metric_name="aruba_last_success_age_seconds",
            label="Last successful collection age",
            boundaries=(0.0, None),
        )
    if collector.refresh_duration_seconds is not None:
        yield Metric("aruba_refresh_duration_seconds", collector.refresh_duration_seconds)

    yield from check_levels(
        float(collector.ap_down),
        levels_upper=params.get("ap_down_upper", ("fixed", (1.0, 5.0))),
        metric_name="aruba_ap_down_checked",
        label="APs not Up",
        boundaries=(0.0, float(collector.ap_total) if collector.ap_total else None),
    )


def discover_access_point(section: Section):
    """Discover access point from the available input data."""
    if section.kind == "ap" and section.access_point is not None:
        yield Service()


def check_access_point(params: Mapping[str, object], section: Section):
    """Evaluate access point and return its resulting state."""
    ap = section.access_point
    if ap is None:
        yield Result(state=State.UNKNOWN, summary="No Aruba Central access-point data")
        return

    ap_state = State.OK if ap.status.lower() == "up" else _state(params.get("status_down_state"), 2)
    yield Result(
        state=ap_state,
        summary=f"Status {ap.status}, {ap.clients} clients, version {ap.version or 'unknown'}",
        details=(
            f"Name: {ap.name or ap.host_name}\nSerial: {ap.serial}\nMAC: {ap.mac}\n"
            f"Model: {ap.model}\nGroup: {ap.group}\nSite: {ap.site}\n"
            f"IP: {ap.ip_address}\nUptime: {ap.uptime}\nSSID count: {ap.ssid_count}"
        ),
    )
    if ap.sleep_status:
        yield Result(state=_state(params.get("sleep_state"), 1), summary="AP sleep status is active")
    if ap.cpu_percent is not None:
        yield from check_levels(
            ap.cpu_percent,
            levels_upper=params.get("cpu_percent_upper", ("fixed", (80.0, 90.0))),
            metric_name="aruba_ap_cpu_percent",
            label="CPU utilization",
            boundaries=(0.0, 100.0),
        )
    memory_free_percent = _ratio(ap.mem_free_mb, ap.mem_total_mb)
    if memory_free_percent is not None:
        yield from check_levels(
            memory_free_percent,
            levels_lower=params.get("mem_free_percent_lower", ("fixed", (20.0, 10.0))),
            metric_name="aruba_ap_mem_free_percent",
            label="Free memory",
            boundaries=(0.0, 100.0),
        )
    clients_levels = params.get("clients_upper")
    if clients_levels:
        yield from check_levels(
            float(ap.clients),
            levels_upper=clients_levels,
            metric_name="aruba_ap_clients",
            label="Connected clients",
            boundaries=(0.0, None),
        )
    else:
        yield Metric("aruba_ap_clients", float(ap.clients))

    expected_firmware = str(params.get("expected_firmware_regex", "") or "").strip()
    if expected_firmware:
        try:
            matches = re.search(expected_firmware, ap.version) is not None
        except re.error as exc:
            yield Result(state=State.UNKNOWN, summary=f"Invalid firmware regular expression: {exc}")
        else:
            if not matches:
                yield Result(state=State.WARN, summary=f"Firmware {ap.version!r} does not match {expected_firmware!r}")

    if ap.mem_total_mb is not None:
        yield Metric("aruba_ap_mem_total_mb", ap.mem_total_mb)
    if ap.mem_free_mb is not None:
        yield Metric("aruba_ap_mem_free_mb", ap.mem_free_mb)
    if ap.uptime_seconds is not None:
        yield Metric("aruba_ap_uptime_seconds", float(ap.uptime_seconds))
    if ap.ssid_count is not None:
        yield Metric("aruba_ap_ssid_count", float(ap.ssid_count))


def discover_radio(section: Section):
    """Discover radio from the available input data."""
    ap = section.access_point
    if section.kind == "ap" and ap is not None:
        for key in sorted(ap.radios):
            yield Service(item=key)


def check_radio(item: str, params: Mapping[str, object], section: Section):
    """Evaluate radio and return its resulting state."""
    ap = section.access_point
    radio = ap.radios.get(item) if ap else None
    if radio is None:
        yield Result(state=State.UNKNOWN, summary=f"Radio {item!r} is missing")
        return
    state = State.OK if radio.status.lower() == "up" else _state(params.get("status_down_state"), 2)
    yield Result(
        state=state,
        summary=f"Status {radio.status}, channel {radio.channel or 'unknown'}, type {radio.radio_type or 'unknown'}",
        details=(
            f"Name: {radio.name}\nIndex: {radio.index}\nBand: {radio.band}\nSpatial stream: {radio.spatial_stream}\n"
            f"Radio MAC: {radio.macaddr}\nTX power: {radio.tx_power if radio.tx_power is not None else 'unknown'} dBm"
        ),
    )
    if radio.utilization is not None:
        yield from check_levels(
            radio.utilization,
            levels_upper=params.get("utilization_upper", ("fixed", (75.0, 90.0))),
            metric_name="aruba_radio_utilization_percent",
            label="Radio utilization",
            boundaries=(0.0, 100.0),
        )
    if radio.tx_power is not None:
        yield Metric("aruba_radio_tx_power_dbm", radio.tx_power)


check_plugin_aruba_central_summary = CheckPlugin(
    name="aruba_central_summary",
    sections=["aruba_central_aps"],
    service_name="Aruba Central summary",
    discovery_function=discover_summary,
    check_function=check_summary,
    check_default_parameters={
        "api_rate_remaining_lower": ("fixed", (500.0, 100.0)),
        "last_success_age_upper": ("fixed", (600.0, 1800.0)),
        "ap_down_upper": ("fixed", (1.0, 5.0)),
    },
    check_ruleset_name="aruba_central_summary",
)

check_plugin_aruba_central_ap = CheckPlugin(
    name="aruba_central_ap",
    sections=["aruba_central_aps"],
    service_name="Aruba Central AP",
    discovery_function=discover_access_point,
    check_function=check_access_point,
    check_default_parameters={
        "status_down_state": 2,
        "sleep_state": 1,
        "cpu_percent_upper": ("fixed", (80.0, 90.0)),
        "mem_free_percent_lower": ("fixed", (20.0, 10.0)),
    },
    check_ruleset_name="aruba_central_ap",
)

check_plugin_aruba_central_radio = CheckPlugin(
    name="aruba_central_radio",
    sections=["aruba_central_aps"],
    service_name="Aruba Central radio %s",
    discovery_function=discover_radio,
    check_function=check_radio,
    check_default_parameters={
        "status_down_state": 2,
        "utilization_upper": ("fixed", (75.0, 90.0)),
    },
    check_ruleset_name="aruba_central_radio",
)
