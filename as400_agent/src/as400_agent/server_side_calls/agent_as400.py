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


class AgentAs400Params(BaseModel):
    """Represent agentas400params behavior and associated state."""
    driver: str
    system: str
    uid: str
    password: Secret


def generate_as400_agent_command(params: AgentAs400Params, host_config: HostConfig):
    """Generate as400 agent command from the current source data."""
    yield SpecialAgentCommand(
        command_arguments=[
            "--driver",
            params.driver,
            "--system",
            params.system,
            "--uid",
            params.uid,
            "--password-id",
            params.password,
        ]
    )


special_agent_as400 = SpecialAgentConfig(
    name = "as400_agent",
    parameter_parser = AgentAs400Params.model_validate,
    commands_function = generate_as400_agent_command,
)
