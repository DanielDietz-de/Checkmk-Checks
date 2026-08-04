#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class AgentSEMUParams(BaseModel):
    username: str
    password: Secret


def generate_semu_agent_command(params: AgentSEMUParams, host_config: HostConfig):
    yield SpecialAgentCommand(
        command_arguments=[
            "--hostname",
            host_config.name,
            "--username",
            params.username,
            "--password-id",
            params.password,
        ]
    )


special_agent_semu = SpecialAgentConfig(
    name = "semu",
    parameter_parser = AgentSEMUParams.model_validate,
    commands_function = generate_semu_agent_command,
)
