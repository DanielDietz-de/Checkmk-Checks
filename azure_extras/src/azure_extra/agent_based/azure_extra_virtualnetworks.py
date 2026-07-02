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


def parse_virtualnetworks(string_table):
    """
    Parse Azure Virtual Networks Properties Data
    """
    if not string_table:
        return {'vnets': {}, 'subnets': {}, 'peerings': {}}
    result = {'vnets': {}, 'subnets': {}, 'peerings': {}}

    for line in string_table:
        if not line:
            continue
        try:
            raw_data = json.loads(line[0])
        except (json.JSONDecodeError, IndexError):
            continue

        if isinstance(raw_data, dict) and 'addressSpace' in raw_data:
            vnet_name = raw_data.get('_resource_name', 'unknown-vnet')

            result['vnets'][vnet_name] = {
                'name': vnet_name,
                'addressSpace': raw_data.get('addressSpace', {}),
                'enableDdosProtection': raw_data.get('enableDdosProtection'),
                'provisioningState': raw_data.get('provisioningState'),
                'resourceGuid': raw_data.get('resourceGuid'),
                'flowLogConfiguration': raw_data.get('flowLogConfiguration', {}),
                'flowLogs': raw_data.get('flowLogs', []),
                '_raw_data': raw_data
            }

            for subnet in raw_data.get('subnets', []):
                subnet_name = subnet.get('name', 'unknown')
                full_name = f"{vnet_name}_{subnet_name}"
                result['subnets'][full_name] = {
                    'name': subnet_name,
                    'vnet_name': vnet_name,
                    'addressPrefix': subnet.get('properties', {}).get('addressPrefix'),
                    'provisioningState': subnet.get('properties', {}).get('provisioningState'),
                    'delegations': subnet.get('properties', {}).get('delegations', []),
                    'ipConfigurations': subnet.get('properties', {}).get('ipConfigurations', []),
                    'serviceEndpoints': subnet.get('properties', {}).get('serviceEndpoints', []),
                    'serviceAssociationLinks': subnet.get('properties', {}).get('serviceAssociationLinks', []),
                    'routeTable': subnet.get('properties', {}).get('routeTable'),
                    'privateEndpointNetworkPolicies': subnet.get('properties', {}).get('privateEndpointNetworkPolicies'),
                    'privateLinkServiceNetworkPolicies': subnet.get('properties', {}).get('privateLinkServiceNetworkPolicies'),
                    '_raw_data': subnet
                }

            for peering in raw_data.get('virtualNetworkPeerings', []):
                peering_name = peering.get('name', 'unknown')
                full_name = f"{vnet_name}_{peering_name}"
                result['peerings'][full_name] = {
                    'name': peering_name,
                    'vnet_name': vnet_name,
                    'peeringState': peering.get('properties', {}).get('peeringState'),
                    'peeringSyncLevel': peering.get('properties', {}).get('peeringSyncLevel'),
                    'provisioningState': peering.get('properties', {}).get('provisioningState'),
                    'allowForwardedTraffic': peering.get('properties', {}).get('allowForwardedTraffic'),
                    'allowGatewayTransit': peering.get('properties', {}).get('allowGatewayTransit'),
                    'allowVirtualNetworkAccess': peering.get('properties', {}).get('allowVirtualNetworkAccess'),
                    'useRemoteGateways': peering.get('properties', {}).get('useRemoteGateways'),
                    'remoteAddressSpace': peering.get('properties', {}).get('remoteAddressSpace', {}),
                    'remoteVirtualNetwork': peering.get('properties', {}).get('remoteVirtualNetwork', {}),
                    '_raw_data': peering
                }

        elif isinstance(raw_data, list):
            for vnet in raw_data:
                vnet_name = vnet.get('name', 'unknown-vnet')
                result['vnets'][vnet_name] = vnet

    return result




# Discovery functions for each resource type
def discover_virtualnetworks(section):
    """
    Discover Azure Virtual Networks
    """
    vnets = section.get('vnets', {})
    for name in vnets:
        yield Service(item=name)


def discover_subnets(section):
    """
    Discover Azure Virtual Network Subnets
    """
    subnets = section.get('subnets', {})
    for name in subnets:
        yield Service(item=name)


def discover_peerings(section):
    """
    Discover Azure Virtual Network Peerings
    """
    peerings = section.get('peerings', {})
    for name in peerings:
        yield Service(item=name)


# Check functions for each resource type
def check_virtualnetwork(item, section):
    """
    Check Azure Virtual Network
    """
    vnets = section.get('vnets', {})
    data = vnets.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary=f"No data for VNet {item}")
        return

    # Check provisioning state
    provisioning_state = data.get('provisioningState', 'Unknown')
    if provisioning_state == 'Succeeded':
        state = State.OK
    elif provisioning_state in ['Failed', 'Canceled']:
        state = State.CRIT
    else:
        state = State.WARN
    
    # Get address space info
    address_prefixes = data.get('addressSpace', {}).get('addressPrefixes', [])
    ddos_protection = data.get('enableDdosProtection', False)
    
    summary_parts = [
        f"State: {provisioning_state}",
        f"Address Space: {', '.join(address_prefixes) if address_prefixes else 'None'}",
        f"DDoS Protection: {'Enabled' if ddos_protection else 'Disabled'}"
    ]

    details = render_details([
        ("Provisioning State", provisioning_state),
        ("Address Space", ', '.join(address_prefixes)),
        ("DDoS Protection", 'Enabled' if ddos_protection else 'Disabled'),
    ])

    yield Result(
        state=state,
        summary="; ".join(summary_parts),
        details=details,
    )
    
    # Add flow log information if available
    flow_logs = data.get('flowLogs', [])
    if flow_logs:
        yield Result(
            state=State.OK,
            summary=f"Flow Logs: {len(flow_logs)} configured"
        )


def check_subnet(item, section):
    """
    Check Azure Virtual Network Subnet
    """
    subnets = section.get('subnets', {})
    data = subnets.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary=f"No data for Subnet {item}")
        return

    # Check provisioning state
    provisioning_state = data.get('provisioningState', 'Unknown')
    if provisioning_state == 'Succeeded':
        state = State.OK
    elif provisioning_state in ['Failed', 'Canceled']:
        state = State.CRIT
    else:
        state = State.WARN
    
    address_prefix = data.get('addressPrefix', 'Unknown')
    delegations = data.get('delegations', [])
    ip_configs = data.get('ipConfigurations', [])
    service_endpoints = data.get('serviceEndpoints', [])
    route_table = data.get('routeTable')
    
    summary_parts = [
        f"State: {provisioning_state}",
        f"Address: {address_prefix}"
    ]
    
    if delegations:
        delegation_names = [d.get('properties', {}).get('serviceName', 'Unknown') for d in delegations]
        summary_parts.append(f"Delegations: {', '.join(delegation_names)}")
    
    if ip_configs:
        summary_parts.append(f"IP Configs: {len(ip_configs)}")
        
    if service_endpoints:
        summary_parts.append(f"Service Endpoints: {len(service_endpoints)}")
        
    if route_table:
        summary_parts.append("Route Table: Configured")

    delegation_names = [d.get('properties', {}).get('serviceName', 'Unknown') for d in delegations]
    endpoint_services = sorted({e.get('service') for e in service_endpoints if e.get('service')})

    details = render_details([
        ("Provisioning State", provisioning_state),
        ("Address Prefix", address_prefix),
        ("Delegations", ', '.join(delegation_names)),
        ("IP Configurations", len(ip_configs) if ip_configs else None),
        ("Service Endpoints", ', '.join(endpoint_services)),
        ("Route Table", short_id(route_table.get('id')) if isinstance(route_table, dict) else None),
    ])

    yield Result(
        state=state,
        summary="; ".join(summary_parts),
        details=details,
    )


def check_peering(item, section):
    """
    Check Azure Virtual Network Peering
    """
    peerings = section.get('peerings', {})
    data = peerings.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary=f"No data for Peering {item}")
        return

    # Check peering state
    peering_state = data.get('peeringState', 'Unknown')
    sync_level = data.get('peeringSyncLevel', 'Unknown')
    provisioning_state = data.get('provisioningState', 'Unknown')
    
    # Determine overall state
    state = State.OK
    if peering_state != 'Connected':
        state = State.WARN
    if sync_level != 'FullyInSync':
        state = State.WARN
    if provisioning_state not in ['Succeeded']:
        state = State.WARN
        
    # Get remote network info
    remote_vnet = data.get('remoteVirtualNetwork', {})
    remote_address_space = data.get('remoteAddressSpace', {}).get('addressPrefixes', [])
    
    remote_name = 'Unknown'
    if remote_vnet.get('id'):
        # Extract remote VNet name from ID
        vnet_id = remote_vnet['id']
        if '/virtualNetworks/' in vnet_id:
            remote_name = vnet_id.split('/virtualNetworks/')[1]
    
    summary_parts = [
        f"State: {peering_state}",
        f"Sync: {sync_level}",
        f"Remote: {remote_name}",
        f"Remote Address: {', '.join(remote_address_space) if remote_address_space else 'None'}"
    ]
    
    # Add traffic settings
    allow_forwarded = data.get('allowForwardedTraffic', False)
    allow_gateway = data.get('allowGatewayTransit', False)
    use_remote_gw = data.get('useRemoteGateways', False)
    
    traffic_settings = []
    if allow_forwarded:
        traffic_settings.append("Forwarded Traffic")
    if allow_gateway:
        traffic_settings.append("Gateway Transit")
    if use_remote_gw:
        traffic_settings.append("Remote Gateway")
        
    if traffic_settings:
        summary_parts.append(f"Features: {', '.join(traffic_settings)}")

    details = render_details([
        ("Peering State", peering_state),
        ("Peering Sync Level", sync_level),
        ("Provisioning State", provisioning_state),
        ("Remote VNet", remote_name),
        ("Remote Address Space", ', '.join(remote_address_space)),
        ("Features", ', '.join(traffic_settings)),
    ])

    yield Result(
        state=state,
        summary="; ".join(summary_parts),
        details=details,
    )

agent_section_azure_extra_virtualnetworks = AgentSection(
    name="azure_extra_virtualnetworks",
    parse_function=parse_virtualnetworks,
)

check_plugin_azure_extra_virtualnetworks = CheckPlugin(
    name="azure_extra_virtualnetworks",
    sections=["azure_extra_virtualnetworks"],
    service_name="Azure Virtual Network %s",
    discovery_function=discover_virtualnetworks,
    check_function=check_virtualnetwork,
)

check_plugin_azure_extra_virtualnetworks_subnets = CheckPlugin(
    name="azure_extra_virtualnetworks_subnets", 
    sections=["azure_extra_virtualnetworks"],
    service_name="Azure Subnet %s",
    discovery_function=discover_subnets,
    check_function=check_subnet,
)

check_plugin_azure_extra_virtualnetworks_peerings = CheckPlugin(
    name="azure_extra_virtualnetworks_peerings",
    sections=["azure_extra_virtualnetworks"], 
    service_name="Azure VNet Peering %s",
    discovery_function=discover_peerings,
    check_function=check_peering,
)
