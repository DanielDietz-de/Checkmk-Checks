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
    timeout: float = 30.0
    ca_file: str | None = None
    no_cert_check: bool = False


def generate_pure_command(params: PureParams, host_config: HostConfig):
    args: list[str | Secret] = [
        "-i",
        host_config.primary_ip_config.address,
        "--token-id",
        params.token,
        "--timeout",
        str(params.timeout),
    ]
    if params.ca_file:
        args.extend(["--ca-file", params.ca_file])
    if params.no_cert_check:
        args.append("--no-cert-check")
    yield SpecialAgentCommand(command_arguments=args)


special_agent_pure = SpecialAgentConfig(
    name="pure",
    parameter_parser=PureParams.model_validate,
    commands_function=generate_pure_command,
)
