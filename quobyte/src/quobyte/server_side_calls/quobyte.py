"""Server-side command wiring for the Quobyte special agent."""

from pydantic import BaseModel
from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class QuobyteParams(BaseModel):
    api_url: str
    username: str
    password: Secret
    timeout: float = 15.0


def generate_quobyte_command(params: QuobyteParams, host_config: HostConfig):
    yield SpecialAgentCommand(
        command_arguments=(
            params.api_url,
            params.username,
            params.password,
            str(params.timeout),
        )
    )


special_agent_quobyte = SpecialAgentConfig(
    name="quobyte",
    parameter_parser=QuobyteParams.model_validate,
    commands_function=generate_quobyte_command,
)
