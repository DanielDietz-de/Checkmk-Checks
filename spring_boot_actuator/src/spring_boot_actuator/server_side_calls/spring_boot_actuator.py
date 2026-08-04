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
    url: str
    username: Optional[str] = None
    password: Optional[Secret] = None
    verify_ssl: bool = True


def generate_spring_boot_actuator_command(
    params: SpringBootActuatorParams, host_config: HostConfig
):
    arguments: list[str | Secret] = ["--url", params.url]
    if params.username:
        arguments.extend(["--username", params.username])
    if params.password is not None:
        arguments.extend(["--password-id", params.password])
    if not params.verify_ssl:
        arguments.append("--no-cert-check")
    yield SpecialAgentCommand(command_arguments=arguments)


special_agent_spring_boot_actuator = SpecialAgentConfig(
    name="spring_boot_actuator",
    parameter_parser=SpringBootActuatorParams.model_validate,
    commands_function=generate_spring_boot_actuator_command,
)
