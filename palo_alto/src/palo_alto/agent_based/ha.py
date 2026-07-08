#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from cmk.agent_based.v2 import (
    CheckPlugin,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    all_of,
    exists,
    startswith,
)


def parse_palo_alto_ha(string_table):
    if not string_table or not string_table[0]:
        return None
    local_state, peer_state, mode = string_table[0]
    return {"local": local_state, "peer": peer_state, "mode": mode}


snmp_section_palo_alto_ha = SimpleSNMPSection(
    name="palo_alto_ha",
    parse_function=parse_palo_alto_ha,
    fetch=SNMPTree(
        # panSysHAState (.11) / panSysHAPeerState (.12) / panSysHAMode (.13)
        base=".1.3.6.1.4.1.25461.2.1.2.1",
        oids=["11", "12", "13"],
    ),
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", "Palo Alto"),
        exists(".1.3.6.1.4.1.25461.2.1.2.1.11.0"),
    ),
)


def discover_palo_alto_ha(section):
    # Only create the service when HA is actually configured.
    if section["mode"].strip().lower() not in ("", "disabled"):
        yield Service()


def check_palo_alto_ha(params, section):
    state_map = params["states"]
    local = section["local"].strip()
    peer = section["peer"].strip()
    mode = section["mode"].strip()

    # Form spec keys have to be valid Python identifiers, so the SNMP state
    # names (e.g. "active-primary") are normalised to underscores for lookup.
    lookup = local.lower().replace("-", "_")
    yield Result(
        state=State(state_map.get(lookup, state_map["default"])),
        summary=f"Local state: {local}",
    )
    yield Result(state=State.OK, notice=f"Peer state: {peer}")
    yield Result(state=State.OK, notice=f"Mode: {mode}")

    # Both members reporting the same active/passive role points to a
    # split-brain / failover problem.
    if local and local.lower() == peer.lower():
        yield Result(
            state=State.WARN,
            summary=f"Local and peer report the same state ({local})",
        )


check_plugin_palo_alto_ha = CheckPlugin(
    name="palo_alto_ha",
    service_name="Palo Alto HA State",
    discovery_function=discover_palo_alto_ha,
    check_function=check_palo_alto_ha,
    check_ruleset_name="palo_alto_ha",
    check_default_parameters={
        "states": {
            "active": 0,
            "passive": 0,
            "active_primary": 0,
            "active_secondary": 0,
            "initial": 1,
            "tentative": 1,
            "suspended": 1,
            "non_functional": 2,
            "unknown": 1,
            "default": 1,
        },
    },
)
