"""Server-side command wiring for the Gravitee management API agent."""

from pydantic import BaseModel
from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class ConfigParser(BaseModel):
    """Represent configparser behavior and associated state."""
    token: Secret
    environment: str = "DEFAULT"
    interval: int = 60
    no_verify_ssl: bool = False
    proxy_url: str | None = None


def agent_arguments(params: ConfigParser, host_config: HostConfig):
    """Handle agent arguments for this module's workflow."""
    args: list[str | Secret] = [
        "--host-name", host_config.name,
        "--token-id", params.token,
        "--environment", params.environment,
        "--interval", str(params.interval),
    ]
    if params.no_verify_ssl:
        args.append("--no-verify-ssl")
    if params.proxy_url:
        args.extend(["--proxy-url", params.proxy_url])
    yield SpecialAgentCommand(command_arguments=args)


special_agent_gravitee_mapi = SpecialAgentConfig(
    name="gravitee_mapi",
    parameter_parser=ConfigParser.model_validate,
    commands_function=agent_arguments,
)
