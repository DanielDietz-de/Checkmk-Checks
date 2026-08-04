#!/usr/bin/env python3
"""Server-side command wiring for Dell EMC PowerMax."""

from collections.abc import Iterator

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class AgentDellPowermaxParams(BaseModel):
    username: str
    password: Secret
    port: int = 8443
    timeout: float = 30.0
    ca_file: str | None = None
    no_cert_check: bool = False


def generate_powermax_command(
    params: AgentDellPowermaxParams,
    host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret] = [
        "-u",
        params.username,
        "--secret-id",
        params.password,
        "-a",
        host_config.ipv4_config.address,
        "--port",
        str(params.port),
        "--timeout",
        str(params.timeout),
    ]
    if params.ca_file:
        args.extend(["--ca-file", params.ca_file])
    if params.no_cert_check:
        args.append("--no-cert-check")
    yield SpecialAgentCommand(command_arguments=args)


special_agent_dellpmax = SpecialAgentConfig(
    name="dellpmax",
    parameter_parser=AgentDellPowermaxParams.model_validate,
    commands_function=generate_powermax_command,
)
