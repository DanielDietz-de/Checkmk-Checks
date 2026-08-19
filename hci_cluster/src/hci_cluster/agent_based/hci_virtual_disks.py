"""Agent-based parsing, discovery, and check logic for hci_cluster: hci virtual disks."""

from .hci_helper import parse_list
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Result,
    State,
    Service,
)

def discovery(section):
    """Handle discovery for this module's workflow."""
    for disk_id in section:
        yield Service(item=disk_id)

def check(item, section):
    """Handle check for this module's workflow."""
    if item not in section:
        return

    data = section[item]
    if data['OperationalStatus'] == 'OK':
        state = State.OK
    else:
        state = State.CRIT

    yield Result(
        state = state,
        summary = 'Health State: {HealthStatus}, Operational State: {OperationalStatus}'.format(**data)
    )

agent_section_hci_virtual_disks = AgentSection(
    name="hci_virtual_disks",
    parse_function=lambda string_table: parse_list(string_table, "FriendlyName"),
)

check_plugin_hci_virtual_disks = CheckPlugin(
    name="hci_virtual_disks",
    service_name="Virtual Disk %s",
    discovery_function=discovery,
    check_function=check,
)
