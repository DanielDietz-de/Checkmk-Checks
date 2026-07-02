#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""
import json

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Service,
    State,
    Result,
    Metric,
)


def parse_properties(string_table):
    """
    Parse Azure Connections Properties Data to Dict
    """
    parsed_data = {}

    for line in string_table:
        if not line:
            continue
        try:
            raw_data = json.loads(line[0])
            connection_name = raw_data.get("_resource_name", "unknown")

            parsed_data[connection_name] = raw_data
        except (json.JSONDecodeError, IndexError):
            continue

    return parsed_data


def parse_metrics(string_table):
    """
    Parse Azure Connections Metrics Data
    """
    parsed_data = {}

    for line in string_table:
        if not line:
            continue
        try:
            metric_data = json.loads(line[0])
            resource_name = metric_data.get('resource_name', 'unknown')
            if resource_name not in parsed_data:
                parsed_data[resource_name] = {}
            metric_name = metric_data.get('metric_name', '')
            parsed_data[resource_name][metric_name] = metric_data
        except (json.JSONDecodeError, IndexError):
            continue

    return parsed_data


def discover_service(section_azure_extra_connections, section_azure_extra_connections_metrics):
    """
    Discover Azure Connections
    """
    for connection_name in section_azure_extra_connections:
        yield Service(item=connection_name)


def check_service(item, section_azure_extra_connections, section_azure_extra_connections_metrics):
    """
    Check Azure Connection Properties
    """
    if item not in section_azure_extra_connections:
        yield Result(state=State.UNKNOWN, summary="Connection not found")
        return

    connection = section_azure_extra_connections[item]

    # Provisioning State
    provisioning_state = connection.get('provisioningState', 'Unknown')
    if provisioning_state == 'Succeeded':
        state = State.OK
    elif provisioning_state in ['Failed', 'Canceled']:
        state = State.CRIT
    else:
        state = State.WARN

    yield Result(state=state, summary=f"Provisioning: {provisioning_state}")

    # Tunnel Connection Status
    tunnel_statuses = connection.get('tunnelConnectionStatus', [])
    if tunnel_statuses:
        for tunnel in tunnel_statuses:
            tunnel_name = tunnel.get('tunnel', 'unknown')
            conn_status = tunnel.get('connectionStatus', 'Unknown')
            ingress = tunnel.get('ingressBytesTransferred', 0)
            egress = tunnel.get('egressBytesTransferred', 0)
            last_established = tunnel.get('lastConnectionEstablishedUtcTime', 'N/A')

            tunnel_state = State.OK if conn_status == 'Connected' else State.CRIT

            def fmt_bytes(b):
                if b >= 1024**3:
                    return f"{b/(1024**3):.2f} GB"
                if b >= 1024**2:
                    return f"{b/(1024**2):.2f} MB"
                if b >= 1024:
                    return f"{b/1024:.2f} KB"
                return f"{b} B"

            yield Result(
                state=tunnel_state,
                summary=f"Tunnel {tunnel_name}: {conn_status}, "
                        f"In: {fmt_bytes(ingress)}, Out: {fmt_bytes(egress)}",
                details=f"Last established: {last_established}"
            )
    else:
        # Fallback: top-level bytes if no tunnelConnectionStatus
        ingress_bytes = connection.get('ingressBytesTransferred', 0)
        egress_bytes = connection.get('egressBytesTransferred', 0)
        if ingress_bytes or egress_bytes:
            yield Result(
                state=State.OK,
                summary=f"Traffic - Ingress: {ingress_bytes} B, Egress: {egress_bytes} B"
            )

    # Connection type info
    connection_type = connection.get('connectionType', 'Unknown')
    connection_protocol = connection.get('connectionProtocol', 'Unknown')
    yield Result(
        state=State.OK,
        summary=f"Type: {connection_type}, Protocol: {connection_protocol}"
    )

    # Metrics: BitsInPerSecond, BitsOutPerSecond
    if section_azure_extra_connections_metrics:
        metrics = section_azure_extra_connections_metrics.get(item, {})
        for metric_name, metric_data in metrics.items():
            value = metric_data.get('value')
            if value is not None:
                unit = metric_data.get('unit', '')
                yield Result(
                    state=State.OK,
                    summary=f"{metric_name}: {value:.2f} {unit}"
                )
                yield Metric(
                    name=metric_name.lower().replace(' ', '_'),
                    value=value
                )


agent_section_azure_extra_connections = AgentSection(
    name="azure_extra_connections",
    parse_function=parse_properties,
)

agent_section_azure_extra_connections_metrics = AgentSection(
    name="azure_extra_connections_metrics",
    parse_function=parse_metrics,
)

check_plugin_azure_extra_connections = CheckPlugin(
    name="azure_extra_connections",
    sections=["azure_extra_connections", "azure_extra_connections_metrics"],
    service_name="Azure Connection %s",
    discovery_function=discover_service,
    check_function=check_service,
)
