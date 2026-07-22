#!/usr/bin/env python
"""Server-side command wiring for Dell EMC PowerMax."""

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


def generate_powermanx_command(
    params: AgentDellPowermaxParams, host_config: HostConfig
):
    print(host_config)
    args: list[str | Secret] = [
        "-u",
        params.username,
        "-s",
        params.password,
        "-a",
        host_config.ipv4_config.address,
    ]
    yield SpecialAgentCommand(command_arguments=args)


special_agent_semu = SpecialAgentConfig(
    name="dellpmax",
    parameter_parser=AgentDellPowermaxParams.model_validate,
    commands_function=generate_powermanx_command,
)
