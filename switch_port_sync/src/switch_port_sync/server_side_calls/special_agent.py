#!/usr/bin/env python3

from collections.abc import Iterable, Mapping

from cmk.server_side_calls.v1 import (
    HostConfig,
    noop_parser,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


def _agent_arguments(
    params: Mapping[str, object], host_config: HostConfig
) -> Iterable[SpecialAgentCommand]:
    host_a = str(params["host_a"])
    host_b = str(params["host_b"])
    current_host = str(host_config.name)

    # One rule is scoped to both pair members. If it is accidentally applied
    # more broadly, do not execute it on unrelated hosts.
    if current_host not in {host_a, host_b}:
        return

    yield SpecialAgentCommand(
        command_arguments=[
            "--pair-name",
            str(params["pair_name"]),
            "--host-a",
            host_a,
            "--host-b",
            host_b,
            "--service-regex",
            str(params.get("service_regex", r"^Interface (?P<item>.+)$")),
        ]
    )


special_agent_switch_port_sync = SpecialAgentConfig(
    name="switch_port_sync",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
