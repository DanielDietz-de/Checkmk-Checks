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


def parse_properties(string_table):
    """
    Parse Azure DNS Resolver Properties Data
    """
    parsed_data = {}

    for line in string_table:
        if not line:
            continue
        try:
            raw_data = json.loads(line[0])
            resolver_name = raw_data.get('_resource_name', raw_data.get('resourceGuid', 'unknown'))
            parsed_data[resolver_name] = raw_data
        except (json.JSONDecodeError, IndexError):
            continue

    return parsed_data


def discover_service(section):
    """
    Discover Azure DNS Resolvers
    """
    for name in section:
        yield Service(item=name)


def check_service(item, section):
    """
    Check Azure DNS Resolver State
    """
    if item not in section:
        yield Result(state=State.UNKNOWN, summary="DNS Resolver not found")
        return

    data = section[item]

    resolver_state = data.get('dnsResolverState', 'Unknown')
    if resolver_state == 'Connected':
        state = State.OK
    elif resolver_state == 'Unknown':
        state = State.WARN
    else:
        state = State.CRIT

    yield Result(state=state, summary=f"DNS Resolver State: {resolver_state}")

    provisioning_state = data.get('provisioningState', 'Unknown')
    if provisioning_state == 'Succeeded':
        prov_state = State.OK
    elif provisioning_state in ['Failed', 'Canceled']:
        prov_state = State.CRIT
    else:
        prov_state = State.WARN

    yield Result(state=prov_state, summary=f"Provisioning: {provisioning_state}")


agent_section_azure_extra_dnsresolvers = AgentSection(
    name="azure_extra_dnsresolvers",
    parse_function=parse_properties,
)

check_plugin_azure_extra_dnsresolvers = CheckPlugin(
    name="azure_extra_dnsresolvers",
    sections=["azure_extra_dnsresolvers"],
    service_name="Azure DNS Resolver %s",
    discovery_function=discover_service,
    check_function=check_service,
)
