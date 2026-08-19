"""Agent-based parsing, discovery, and check logic for cohesity: cohesity node status."""

# 2021 created by Sven Rueß, sritd.de

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Service,
    Result,
    State,
)


def parse_cohesity_node_status(string_table):
    """Parse cohesity node status into its normalized representation."""
    section = {}
    for row in string_table:
        item = row[0]
        section.setdefault(item, {})

        status = row[1]
        services = []
        if row[2:]:
            services = (row[2:][0]).split(',')
        section[item][status] = services
    return section


agent_section_cohesity_node_status = AgentSection(
    name="cohesity_node_status",
    parse_function=parse_cohesity_node_status,
)


def discovery_cohesity_node_status(section):
    """Handle discovery cohesity node status for this module's workflow."""
    for node in section.keys():
        yield Service(item=node)

def check_cohesity_node_status(item, params, section):
    """Evaluate cohesity node status and return its resulting state."""
    services = params.get('services', [])

    if item in section.keys():
        for service in services:
            if service in section[item]['ok']:
                section[item]['ok'].remove(service)

            if service in section[item]['failed']:
                section[item]['failed'].remove(service)

        if "ok" in section[item] and len(section[item]["ok"]):
            yield Result(
                state=State.OK,
                summary=f"{len(section[item]['ok']) } Services are OK",
                details=f"Services OK: {', '.join(section[item]['ok'])}"
            )

        if "failed" in section[item] and len(section[item]["failed"]):
            yield Result(
                state=State.CRIT,
                summary=f"{len(section[item]['failed'])} Services are failed",
                details=f"Services FAILED: {', '.join(section[item]['failed'])}"
            )


check_plugin_cohesity_node_status = CheckPlugin(
    name="cohesity_node_status",
    service_name="Node Status %s",
    discovery_function=discovery_cohesity_node_status,
    check_function=check_cohesity_node_status,
    check_default_parameters={},
    check_ruleset_name="cohesity_node_status",
)
