"""Server-side command wiring for the Veritas Flex special agent."""

from typing import Optional

from pydantic import BaseModel
from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class VeritasParams(BaseModel):
    api_url: str
    username: str
    password: Secret
    ca_file: Optional[str] = None
    no_cert_check: bool = False


def generate_veritas_command(params: VeritasParams, host_config: HostConfig):
    if params.ca_file and params.no_cert_check:
        raise ValueError("ca_file and no_cert_check are mutually exclusive")
    arguments: list[str | Secret] = [
        params.api_url, "-u", params.username, "--password-id", params.password
    ]
    if params.ca_file:
        arguments.extend(("--ca-file", params.ca_file))
    elif params.no_cert_check:
        arguments.append("--no-cert-check")
    yield SpecialAgentCommand(command_arguments=arguments)


special_agent_veritas = SpecialAgentConfig(
    name="veritas",
    parameter_parser=VeritasParams.model_validate,
    commands_function=generate_veritas_command,
)
