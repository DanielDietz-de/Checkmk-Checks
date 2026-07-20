#!/usr/bin/env python3

from collections.abc import Iterable, Mapping

from cmk.server_side_calls.v1 import (
    HostConfig,
    noop_parser,
    SpecialAgentCommand,
    SpecialAgentConfig,
)

_REQUIRED_PARAMETERS = ("pair_name", "host_a", "host_b", "service_regex")


def _required_parameter(
    params: Mapping[str, object], key: str, *, strip: bool = True
) -> str:
    if key not in params:
        raise ValueError(f"Missing required switch_port_sync parameter: {key}")

    value = str(params[key])
    if not value.strip():
        raise ValueError(f"Empty required switch_port_sync parameter: {key}")
    return value.strip() if strip else value


def _agent_arguments(
    params: Mapping[str, object], host_config: HostConfig
) -> Iterable[SpecialAgentCommand]:
    missing = [key for key in _REQUIRED_PARAMETERS if key not in params]
    if missing:
        raise ValueError(
            "Missing required switch_port_sync parameters: " + ", ".join(missing)
        )

    pair_name = _required_parameter(params, "pair_name")
    host_a = _required_parameter(params, "host_a")
    host_b = _required_parameter(params, "host_b")
    service_regex = _required_parameter(params, "service_regex", strip=False)
    current_host = str(host_config.name)

    # One rule is scoped to both pair members. If it is accidentally applied
    # more broadly, do not execute it on unrelated hosts.
    if current_host not in {host_a, host_b}:
        return

    yield SpecialAgentCommand(
        command_arguments=[
            "--pair-name",
            pair_name,
            "--host-a",
            host_a,
            "--host-b",
            host_b,
            "--service-regex",
            service_regex,
        ]
    )


special_agent_switch_port_sync = SpecialAgentConfig(
    name="switch_port_sync",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
