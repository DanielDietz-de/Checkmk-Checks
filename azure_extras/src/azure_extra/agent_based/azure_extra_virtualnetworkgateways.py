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


def short_id(resource_id):
    """
    Return the last path segment (the resource name) of an Azure resource ID.
    """
    if not resource_id or not isinstance(resource_id, str):
        return None
    return resource_id.rstrip('/').split('/')[-1]


def render_details(pairs):
    """
    Render a list of (label, value) pairs as readable multi-line details.
    Empty values are skipped so we never show noise or dump raw JSON.
    """
    lines = []
    for label, value in pairs:
        if value in (None, '', {}, [], 'None', 'Unknown'):
            continue
        lines.append(f"{label}: {value}")
    return "\n".join(lines)


def parse_properties(string_table):
    """
    Parse Azure Virtual Network Gateways Properties Data
    """
    if not string_table:
        return {'gateways': {}, 'ip_configs': {}, 'bgp_settings': {}, 'vpn_clients': {}, 'remote_peerings': {}, 'nat_rules': {}, 'policy_groups': {}}
    result = {'gateways': {}, 'ip_configs': {}, 'bgp_settings': {}, 'vpn_clients': {}, 'remote_peerings': {}, 'nat_rules': {}, 'policy_groups': {}}

    for line in string_table:
        if not line:
            continue
        try:
            raw_data = json.loads(line[0])
        except (json.JSONDecodeError, IndexError):
            continue

        if not isinstance(raw_data, dict):
            continue

        gateway_name = raw_data.get('_resource_name', raw_data.get('resourceGuid', 'unknown-gateway'))

        result['gateways'][gateway_name] = {
            'name': gateway_name,
            'provisioningState': raw_data.get('provisioningState'),
            'resourceGuid': raw_data.get('resourceGuid'),
            'packetCaptureDiagnosticState': raw_data.get('packetCaptureDiagnosticState'),
            'enablePrivateIpAddress': raw_data.get('enablePrivateIpAddress'),
            'isMigrateToCSES': raw_data.get('isMigrateToCSES'),
            'gatewayType': raw_data.get('gatewayType'),
            'vpnType': raw_data.get('vpnType'),
            'enableBgp': raw_data.get('enableBgp'),
            'activeActive': raw_data.get('activeActive'),
            'sku': raw_data.get('sku', {}),
            'vpnGatewayGeneration': raw_data.get('vpnGatewayGeneration'),
            'allowRemoteVnetTraffic': raw_data.get('allowRemoteVnetTraffic'),
            'allowVirtualWanTraffic': raw_data.get('allowVirtualWanTraffic'),
            'virtualNetworkGatewayMigrationStatus': raw_data.get('virtualNetworkGatewayMigrationStatus', {}),
            '_raw_data': raw_data
        }

        for ip_config in raw_data.get('ipConfigurations', []):
            ip_config_name = ip_config.get('name', 'unknown')
            full_name = f"{gateway_name}_{ip_config_name}"
            result['ip_configs'][full_name] = {
                'name': ip_config_name,
                'gateway_name': gateway_name,
                'provisioningState': ip_config.get('properties', {}).get('provisioningState'),
                'privateIPAllocationMethod': ip_config.get('properties', {}).get('privateIPAllocationMethod'),
                'publicIPAddress': ip_config.get('properties', {}).get('publicIPAddress', {}),
                'subnet': ip_config.get('properties', {}).get('subnet', {}),
                '_raw_data': ip_config
            }

        bgp_settings = raw_data.get('bgpSettings', {})
        if bgp_settings:
            bgp_name = f"{gateway_name}_bgp"
            result['bgp_settings'][bgp_name] = {
                'name': bgp_name,
                'gateway_name': gateway_name,
                'asn': bgp_settings.get('asn'),
                'bgpPeeringAddress': bgp_settings.get('bgpPeeringAddress'),
                'peerWeight': bgp_settings.get('peerWeight'),
                'bgpPeeringAddresses': bgp_settings.get('bgpPeeringAddresses', []),
                '_raw_data': bgp_settings
            }

        vpn_client_config = raw_data.get('vpnClientConfiguration', {})
        if vpn_client_config:
            vpn_client_name = f"{gateway_name}_vpnclient"
            result['vpn_clients'][vpn_client_name] = {
                'name': vpn_client_name,
                'gateway_name': gateway_name,
                'vpnClientProtocols': vpn_client_config.get('vpnClientProtocols', []),
                'vpnAuthenticationTypes': vpn_client_config.get('vpnAuthenticationTypes', []),
                'vpnClientRootCertificates': vpn_client_config.get('vpnClientRootCertificates', []),
                'vpnClientRevokedCertificates': vpn_client_config.get('vpnClientRevokedCertificates', []),
                'vngClientConnectionConfigurations': vpn_client_config.get('vngClientConnectionConfigurations', []),
                'radiusServers': vpn_client_config.get('radiusServers', []),
                'vpnClientIpsecPolicies': vpn_client_config.get('vpnClientIpsecPolicies', []),
                '_raw_data': vpn_client_config
            }

        for idx, peering in enumerate(raw_data.get('remoteVirtualNetworkPeerings', [])):
            if isinstance(peering, dict) and peering.get('id'):
                peering_id = peering['id']
                peering_name = peering_id.split('/')[-1] if peering_id else f'unknown-peering-{idx}'
                full_name = f"{gateway_name}_{peering_name}"
                result['remote_peerings'][full_name] = {
                    'name': peering_name,
                    'gateway_name': gateway_name,
                    'peering_id': peering_id,
                    '_raw_data': peering
                }

        for nat_rule in raw_data.get('natRules', []):
            nat_rule_name = nat_rule.get('name', 'unknown')
            full_name = f"{gateway_name}_{nat_rule_name}"
            result['nat_rules'][full_name] = {
                'name': nat_rule_name,
                'gateway_name': gateway_name,
                '_raw_data': nat_rule
            }

        for policy_group in raw_data.get('virtualNetworkGatewayPolicyGroups', []):
            policy_group_name = policy_group.get('name', 'unknown')
            full_name = f"{gateway_name}_{policy_group_name}"
            result['policy_groups'][full_name] = {
                'name': policy_group_name,
                'gateway_name': gateway_name,
                '_raw_data': policy_group
            }

    return result


# Discovery functions for each resource type
def discover_gateways(section):
    """
    Discover Azure Virtual Network Gateways
    """
    gateways = section.get('gateways', {})
    for name in gateways:
        yield Service(item=name)


def discover_ip_configs(section):
    """
    Discover Azure VPN Gateway IP Configurations
    """
    ip_configs = section.get('ip_configs', {})
    for name in ip_configs:
        yield Service(item=name)


def discover_bgp_settings(section):
    """
    Discover Azure VPN Gateway BGP Settings
    """
    bgp_settings = section.get('bgp_settings', {})
    for name in bgp_settings:
        yield Service(item=name)


def discover_vpn_clients(section):
    """
    Discover Azure VPN Gateway VPN Client Configurations
    """
    vpn_clients = section.get('vpn_clients', {})
    for name in vpn_clients:
        yield Service(item=name)


def discover_remote_peerings(section):
    """
    Discover Azure VPN Gateway Remote VNet Peerings
    """
    remote_peerings = section.get('remote_peerings', {})
    for name in remote_peerings:
        yield Service(item=name)


def discover_nat_rules(section):
    """
    Discover Azure VPN Gateway NAT Rules
    """
    nat_rules = section.get('nat_rules', {})
    for name in nat_rules:
        yield Service(item=name)


def discover_policy_groups(section):
    """
    Discover Azure VPN Gateway Policy Groups
    """
    policy_groups = section.get('policy_groups', {})
    for name in policy_groups:
        yield Service(item=name)


# Check functions for each resource type
def check_gateway(item, section):
    """
    Check Azure Virtual Network Gateway Main Properties
    """
    gateways = section.get('gateways', {})
    data = gateways.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary=f"No data for Gateway {item}")
        return

    # Check provisioning state
    provisioning_state = data.get('provisioningState', 'Unknown')
    if provisioning_state == 'Succeeded':
        state = State.OK
    elif provisioning_state in ['Failed', 'Canceled']:
        state = State.CRIT
    else:
        state = State.WARN
    
    # Get main properties
    gateway_type = data.get('gatewayType', 'Unknown')
    vpn_type = data.get('vpnType', 'Unknown')
    sku = data.get('sku', {})
    sku_name = sku.get('name', 'Unknown')
    sku_tier = sku.get('tier', 'Unknown')
    sku_capacity = sku.get('capacity', 'Unknown')
    active_active = data.get('activeActive', False)
    enable_bgp = data.get('enableBgp', False)
    generation = data.get('vpnGatewayGeneration', 'Unknown')
    
    summary_parts = [
        f"State: {provisioning_state}",
        f"Type: {gateway_type} ({vpn_type})",
        f"SKU: {sku_name} ({sku_tier})",
        f"Capacity: {sku_capacity}",
        f"Mode: {'Active-Active' if active_active else 'Active-Standby'}",
        f"BGP: {'Enabled' if enable_bgp else 'Disabled'}",
        f"Generation: {generation}"
    ]
    
    details = render_details([
        ("Provisioning State", provisioning_state),
        ("Gateway Type", gateway_type),
        ("VPN Type", vpn_type),
        ("SKU", f"{sku_name} ({sku_tier})"),
        ("Capacity", sku_capacity),
        ("Mode", 'Active-Active' if active_active else 'Active-Standby'),
        ("BGP", 'Enabled' if enable_bgp else 'Disabled'),
        ("Generation", generation),
    ])

    yield Result(
        state=state,
        summary="; ".join(summary_parts),
        details=details,
    )

    # Check migration status
    migration_status = data.get('virtualNetworkGatewayMigrationStatus', {})
    migration_state = migration_status.get('state', 'None')
    if migration_state != 'None':
        migration_phase = migration_status.get('phase', 'Unknown')
        error_message = migration_status.get('errorMessage', '')
        
        if error_message:
            yield Result(
                state=State.WARN,
                summary=f"Migration: {migration_state} ({migration_phase}) - {error_message}"
            )
        else:
            yield Result(
                state=State.OK,
                summary=f"Migration: {migration_state} ({migration_phase})"
            )


def check_ip_config(item, section):
    """
    Check Azure VPN Gateway IP Configuration
    """
    ip_configs = section.get('ip_configs', {})
    data = ip_configs.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary=f"No data for IP Config {item}")
        return

    # Check provisioning state
    provisioning_state = data.get('provisioningState', 'Unknown')
    if provisioning_state == 'Succeeded':
        state = State.OK
    elif provisioning_state in ['Failed', 'Canceled']:
        state = State.CRIT
    else:
        state = State.WARN
    
    allocation_method = data.get('privateIPAllocationMethod', 'Unknown')
    public_ip_id = data.get('publicIPAddress', {}).get('id', '')
    public_ip_name = public_ip_id.split('/')[-1] if public_ip_id else 'None'
    subnet_id = data.get('subnet', {}).get('id', '')
    subnet_name = subnet_id.split('/')[-1] if subnet_id else 'None'
    
    summary_parts = [
        f"State: {provisioning_state}",
        f"IP Allocation: {allocation_method}",
        f"Public IP: {public_ip_name}",
        f"Subnet: {subnet_name}"
    ]

    details = render_details([
        ("Provisioning State", provisioning_state),
        ("IP Allocation Method", allocation_method),
        ("Public IP", public_ip_name),
        ("Subnet", subnet_name),
    ])

    yield Result(
        state=state,
        summary="; ".join(summary_parts),
        details=details,
    )


def check_bgp_settings(item, section):
    """
    Check Azure VPN Gateway BGP Settings
    """
    bgp_settings = section.get('bgp_settings', {})
    data = bgp_settings.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary=f"No data for BGP Settings {item}")
        return

    asn = data.get('asn', 'Unknown')
    bgp_peering_address = data.get('bgpPeeringAddress', 'Unknown')
    peer_weight = data.get('peerWeight', 'Unknown')
    peering_addresses = data.get('bgpPeeringAddresses', [])
    
    summary_parts = [
        f"ASN: {asn}",
        f"Peering Address: {bgp_peering_address}",
        f"Peer Weight: {peer_weight}",
        f"Peering IPs: {len(peering_addresses)}"
    ]

    details = render_details([
        ("ASN", asn),
        ("BGP Peering Address", bgp_peering_address),
        ("Peer Weight", peer_weight),
        ("Number of Peering IPs", len(peering_addresses)),
    ])

    yield Result(
        state=State.OK,
        summary="; ".join(summary_parts),
        details=details,
    )
    
    # Check individual peering addresses
    for peering_addr in peering_addresses:
        tunnel_ips = peering_addr.get('tunnelIpAddresses', [])
        default_bgp_ips = peering_addr.get('defaultBgpIpAddresses', [])
        
        if tunnel_ips:
            yield Result(
                state=State.OK,
                summary=f"Tunnel IPs: {', '.join(tunnel_ips)}, BGP IPs: {', '.join(default_bgp_ips)}"
            )


def check_vpn_client(item, section):
    """
    Check Azure VPN Gateway VPN Client Configuration
    """
    vpn_clients = section.get('vpn_clients', {})
    data = vpn_clients.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary=f"No data for VPN Client Config {item}")
        return

    protocols = data.get('vpnClientProtocols', [])
    auth_types = data.get('vpnAuthenticationTypes', [])
    root_certs = data.get('vpnClientRootCertificates', [])
    revoked_certs = data.get('vpnClientRevokedCertificates', [])
    radius_servers = data.get('radiusServers', [])
    ipsec_policies = data.get('vpnClientIpsecPolicies', [])
    
    summary_parts = [
        f"Protocols: {', '.join(protocols) if protocols else 'None'}",
        f"Auth Types: {', '.join(auth_types) if auth_types else 'None'}",
        f"Root Certs: {len(root_certs)}",
        f"Revoked Certs: {len(revoked_certs)}",
        f"RADIUS: {len(radius_servers)}",
        f"IPSec Policies: {len(ipsec_policies)}"
    ]

    details = render_details([
        ("VPN Client Protocols", ', '.join(protocols)),
        ("Authentication Types", ', '.join(auth_types)),
        ("Root Certificates", len(root_certs)),
        ("Revoked Certificates", len(revoked_certs)),
        ("RADIUS Servers", len(radius_servers)),
        ("IPSec Policies", len(ipsec_policies)),
    ])

    yield Result(
        state=State.OK,
        summary="; ".join(summary_parts),
        details=details,
    )


def check_remote_peering(item, section):
    """
    Check Azure VPN Gateway Remote VNet Peering
    """
    remote_peerings = section.get('remote_peerings', {})
    data = remote_peerings.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary=f"No data for Remote Peering {item}")
        return

    peering_id = data.get('peering_id', 'Unknown')
    
    # Extract useful information from the peering ID
    if '/virtualNetworks/' in peering_id and '/virtualNetworkPeerings/' in peering_id:
        parts = peering_id.split('/')
        subscription_id = parts[2] if len(parts) > 2 else 'Unknown'
        resource_group = parts[4] if len(parts) > 4 else 'Unknown'
        vnet_name = parts[8] if len(parts) > 8 else 'Unknown'
        peering_name = parts[10] if len(parts) > 10 else 'Unknown'
        
        summary_parts = [
            f"VNet: {vnet_name}",
            f"Resource Group: {resource_group}",
            f"Subscription: {subscription_id[:8]}...",
            f"Peering: {peering_name}"
        ]

        details = render_details([
            ("Remote VNet", vnet_name),
            ("Resource Group", resource_group),
            ("Subscription", subscription_id),
            ("Peering Name", peering_name),
        ])

        yield Result(
            state=State.OK,
            summary="; ".join(summary_parts),
            details=details,
        )
    else:
        yield Result(
            state=State.OK,
            summary=f"Peering ID: {peering_id}",
            details=render_details([("Peering", short_id(peering_id) or peering_id)]),
        )


def check_nat_rule(item, section):
    """
    Check Azure VPN Gateway NAT Rule
    """
    nat_rules = section.get('nat_rules', {})
    data = nat_rules.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary=f"No data for NAT Rule {item}")
        return

    # Since NAT rules appear to be empty in the provided data, just confirm existence
    yield Result(
        state=State.OK,
        summary=f"NAT Rule: {data.get('name', 'Unknown')}",
        details=render_details([("NAT Rule", data.get('name'))]),
    )


def check_policy_group(item, section):
    """
    Check Azure VPN Gateway Policy Group
    """
    policy_groups = section.get('policy_groups', {})
    data = policy_groups.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary=f"No data for Policy Group {item}")
        return

    # Since policy groups appear to be empty in the provided data, just confirm existence
    yield Result(
        state=State.OK,
        summary=f"Policy Group: {data.get('name', 'Unknown')}",
        details=render_details([("Policy Group", data.get('name'))]),
    )


def parse_metrics(string_table):
    """
    Parse Azure VPN Gateway Metrics Data.
    Key includes dimension (e.g. BGP peer IP) so multiple entries per metric are preserved.
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
            dimension = metric_data.get('dimension', '')
            key = f"{metric_name}_{dimension}" if dimension else metric_name
            parsed_data[resource_name][key] = metric_data
        except (json.JSONDecodeError, IndexError):
            continue
    return parsed_data


def discover_gateway_metrics(section):
    """
    Discover Azure VPN Gateway resources that have metrics
    """
    for resource_name in section:
        yield Service(item=resource_name)


def check_gateway_metrics(item, section):
    """
    Check Azure VPN Gateway Metrics (BgpPeerStatus, BgpRoutesAdvertised, packet drops, etc.)
    """
    metrics = section.get(item)
    if not metrics:
        yield Result(state=State.UNKNOWN, summary=f"No metrics for {item}")
        return

    # BgpPeerStatus may appear multiple times (once per BGP peer IP)
    for entry_key, entry_data in metrics.items():
        if not entry_key.startswith('BgpPeerStatus'):
            continue
        value = entry_data.get('value')
        if value is None:
            continue
        ip = entry_data.get('dimension', '')
        label = f"BGP Peer Status ({ip})" if ip else "BGP Peer Status"
        # 0=Unknown…7=Various, 8=Established, 9-11=Pending changes
        bgp_state = State.OK if value >= 8 else State.WARN
        yield Result(state=bgp_state, summary=f"{label}: {value:.0f}")
        metric_key = f"bgp_peer_status_{ip.replace('.', '_')}" if ip else "bgp_peer_status"
        yield Metric(metric_key, value)

    for prefix in ('BgpRoutesAdvertised', 'BgpRoutesLearned',
                   'TunnelEgressPacketDropCount', 'TunnelIngressPacketDropCount'):
        for entry_key, entry_data in metrics.items():
            if not entry_key.startswith(prefix):
                continue
            value = entry_data.get('value')
            if value is None:
                continue
            ip = entry_data.get('dimension', '')
            unit = entry_data.get('unit', '')
            label = f"{prefix} ({ip})" if ip else prefix
            summary = f"{label}: {value:.2f} {unit}".strip()
            yield Result(state=State.OK, summary=summary)
            metric_key = f"{prefix.lower()}_{ip.replace('.', '_')}" if ip else prefix.lower()
            yield Metric(metric_key, value)


agent_section_azure_extra_virtualnetworkgateways = AgentSection(
    name="azure_extra_virtualnetworkgateways",
    parse_function=parse_properties,
)

agent_section_azure_extra_virtualnetworkgateways_metrics = AgentSection(
    name="azure_extra_virtualnetworkgateways_metrics",
    parse_function=parse_metrics,
)

# Check plugins for each resource type
check_plugin_azure_vpn_gateway = CheckPlugin(
    name="azure_vpn_gateway",
    sections=["azure_extra_virtualnetworkgateways"],
    service_name="Azure VPN Gateway %s",
    discovery_function=discover_gateways,
    check_function=check_gateway,
)

check_plugin_azure_vpn_gateway_ipconfig = CheckPlugin(
    name="azure_vpn_gateway_ipconfig",
    sections=["azure_extra_virtualnetworkgateways"],
    service_name="Azure VPN Gateway IP Config %s",
    discovery_function=discover_ip_configs,
    check_function=check_ip_config,
)

check_plugin_azure_vpn_gateway_bgp = CheckPlugin(
    name="azure_vpn_gateway_bgp",
    sections=["azure_extra_virtualnetworkgateways"],
    service_name="Azure VPN Gateway BGP %s",
    discovery_function=discover_bgp_settings,
    check_function=check_bgp_settings,
)

check_plugin_azure_vpn_gateway_vpnclient = CheckPlugin(
    name="azure_vpn_gateway_vpnclient",
    sections=["azure_extra_virtualnetworkgateways"],
    service_name="Azure VPN Gateway VPN Client %s",
    discovery_function=discover_vpn_clients,
    check_function=check_vpn_client,
)

check_plugin_azure_vpn_gateway_remotepeering = CheckPlugin(
    name="azure_vpn_gateway_remotepeering",
    sections=["azure_extra_virtualnetworkgateways"],
    service_name="Azure VPN Gateway Remote Peering %s",
    discovery_function=discover_remote_peerings,
    check_function=check_remote_peering,
)

check_plugin_azure_vpn_gateway_natrule = CheckPlugin(
    name="azure_vpn_gateway_natrule",
    sections=["azure_extra_virtualnetworkgateways"],
    service_name="Azure VPN Gateway NAT Rule %s",
    discovery_function=discover_nat_rules,
    check_function=check_nat_rule,
)

check_plugin_azure_vpn_gateway_policygroup = CheckPlugin(
    name="azure_vpn_gateway_policygroup",
    sections=["azure_extra_virtualnetworkgateways"],
    service_name="Azure VPN Gateway Policy Group %s",
    discovery_function=discover_policy_groups,
    check_function=check_policy_group,
)

check_plugin_azure_vpn_gateway_metrics = CheckPlugin(
    name="azure_vpn_gateway_metrics",
    sections=["azure_extra_virtualnetworkgateways_metrics"],
    service_name="Azure VPN Gateway Metrics %s",
    discovery_function=discover_gateway_metrics,
    check_function=check_gateway_metrics,
)
