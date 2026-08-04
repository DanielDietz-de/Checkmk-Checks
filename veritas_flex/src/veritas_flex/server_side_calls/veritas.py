"""Server-side command wiring for the Veritas Flex special agent."""

from pydantic import BaseModel
from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class VeritasParams(BaseModel):
    api_url: str
    username: str
    password: Secret


def generate_veritas_command(params: VeritasParams, host_config: HostConfig):
    yield SpecialAgentCommand(
        command_arguments=(
            params.api_url,
            "-u", params.username,
            "-p", params.password,
        )
    )


special_agent_veritas = SpecialAgentConfig(
    name="veritas",
    parameter_parser=VeritasParams.model_validate,
    commands_function=generate_veritas_command,
)
