#!/usr/bin/env python3
"""Server-side command wiring for Pure Storage."""

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class PureParams(BaseModel):
    token: Secret


def generate_pure_command(params: PureParams, host_config: HostConfig):
    args: list[str | Secret] = [
        "-i",
        host_config.primary_ip_config.address,
        "-t",
        params.token,
    ]
    yield SpecialAgentCommand(command_arguments=args)


special_agent_pure = SpecialAgentConfig(
    name="pure",
    parameter_parser=PureParams.model_validate,
    commands_function=generate_pure_command,
)
