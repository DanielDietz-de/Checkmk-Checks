#!/usr/bin/env python3
"""Server-side command wiring for Spring Boot Actuator."""

from typing import Optional

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class SpringBootActuatorParams(BaseModel):
    """Represent springbootactuatorparams behavior and associated state."""
    url: str
    username: Optional[str] = None
    password: Optional[Secret] = None
    verify_ssl: bool = True
    ca_file: Optional[str] = None


def generate_spring_boot_actuator_command(
    params: SpringBootActuatorParams, host_config: HostConfig
):
    """Generate spring boot actuator command from the current source data."""
    arguments: list[str | Secret] = ["--url", params.url]
    if params.username:
        arguments.extend(["--username", params.username])
    if params.password is not None:
        arguments.extend(["--password-id", params.password])
    if params.ca_file and not params.verify_ssl:
        raise ValueError("ca_file and verify_ssl=False are mutually exclusive")
    if params.ca_file:
        arguments.extend(["--ca-file", params.ca_file])
    elif not params.verify_ssl:
        arguments.append("--no-cert-check")
    yield SpecialAgentCommand(command_arguments=arguments)


special_agent_spring_boot_actuator = SpecialAgentConfig(
    name="spring_boot_actuator",
    parameter_parser=SpringBootActuatorParams.model_validate,
    commands_function=generate_spring_boot_actuator_command,
)
