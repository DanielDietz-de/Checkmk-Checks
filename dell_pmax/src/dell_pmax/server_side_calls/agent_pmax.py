#!/usr/bin/env python3
"""Server-side command wiring for Dell EMC PowerMax."""

from typing import Optional

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class AgentDellPowermaxParams(BaseModel):
    username: str
    password: Secret
    port: int = Field(default=8443, ge=1, le=65535)
    api_version: int = Field(default=100, ge=1, le=999)
    timeout: float = Field(default=15.0, ge=0.5, le=120)
    ca_bundle: Optional[str] = None


def generate_powermanx_command(
    params: AgentDellPowermaxParams, host_config: HostConfig
):
    try:
        address = host_config.primary_ip_config.address
    except AttributeError:
        address = host_config.ipv4_config.address

    args: list[str | Secret] = [
        "--username",
        params.username,
        "--secret",
        params.password,
        "--address",
        address,
        "--port",
        str(params.port),
        "--api-version",
        str(params.api_version),
        "--timeout",
        str(params.timeout),
    ]
    if params.ca_bundle:
        args.extend(("--ca-bundle", params.ca_bundle))
    yield SpecialAgentCommand(command_arguments=args)


special_agent_semu = SpecialAgentConfig(
    name="dellpmax",
    parameter_parser=AgentDellPowermaxParams.model_validate,
    commands_function=generate_powermanx_command,
)
