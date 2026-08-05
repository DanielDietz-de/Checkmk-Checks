"""Server-side command construction for the arcgis_portal integration."""

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class ConfigParser(BaseModel):
    """Validated ArcGIS special-agent configuration."""

    username: str
    password: Secret
    proxy_url: str | None = None
    debug: bool = False


def agent_arguments(params: ConfigParser, host_config: HostConfig):
    """Build a secret-aware special-agent command line."""
    args: list[str | Secret] = [
        "--host-name",
        host_config.name,
        "--username",
        params.username,
        "--password-id",
        params.password,
    ]
    if params.proxy_url:
        args.extend(["--proxy-url", params.proxy_url])
    if params.debug:
        args.append("--debug")
    yield SpecialAgentCommand(command_arguments=args)


special_agent_agent = SpecialAgentConfig(
    name="arcgis_portal",
    parameter_parser=ConfigParser.model_validate,
    commands_function=agent_arguments,
)
