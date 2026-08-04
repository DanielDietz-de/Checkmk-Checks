#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from pydantic import BaseModel, model_validator

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class AgentSEMUParams(BaseModel):
    """Validated SEMU special-agent parameters supplied by the ruleset."""

    username: str
    password: Secret
    ca_file: str | None = None
    no_cert_check: bool = False

    @model_validator(mode="after")
    def _validate_tls_options(self) -> "AgentSEMUParams":
        """Reject contradictory TLS settings before constructing a command."""
        if self.ca_file and self.no_cert_check:
            raise ValueError("ca_file and no_cert_check are mutually exclusive")
        return self


def generate_semu_agent_command(params: AgentSEMUParams, host_config: HostConfig):
    """Build the special-agent command without exposing the stored password."""
    command_arguments = [
        "--hostname",
        host_config.name,
        "--username",
        params.username,
        "--password-id",
        params.password,
    ]
    if params.ca_file:
        command_arguments.extend(["--ca-file", params.ca_file])
    if params.no_cert_check:
        command_arguments.append("--no-cert-check")

    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_semu = SpecialAgentConfig(
    name="semu",
    parameter_parser=AgentSEMUParams.model_validate,
    commands_function=generate_semu_agent_command,
)
