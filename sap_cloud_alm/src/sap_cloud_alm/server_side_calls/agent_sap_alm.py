"""Server-side command wiring for the SAP Cloud ALM special agent."""

from urllib.parse import quote_plus
from pydantic import BaseModel
from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class AgentSapAlmParams(BaseModel):
    """Represent agentsapalmparams behavior and associated state."""
    instance: str
    client_id: str
    metric_filter: str
    client_secret: Secret
    proxy: str | None = None


def generate_agent_command(params: AgentSapAlmParams, host_config: HostConfig):
    """Generate agent command from the current source data."""
    args: list[str | Secret] = [
        "--instance", params.instance,
        "--client-id", params.client_id,
        "--client-secret-id", params.client_secret,
        "--filter", quote_plus(params.metric_filter),
    ]
    if params.proxy:
        args.extend(("--proxy", params.proxy))
    yield SpecialAgentCommand(command_arguments=args)


special_agent_sap_cloud_alm = SpecialAgentConfig(
    name="sap_cloud_alm",
    parameter_parser=AgentSapAlmParams.model_validate,
    commands_function=generate_agent_command,
)
