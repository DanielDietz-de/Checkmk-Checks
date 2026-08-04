"""
ADFS Certificate Special Agent - Server Side Calls

Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""
from pydantic import BaseModel
from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig


class ConfigParser(BaseModel):
    """
    Config Parser
    """
    proxy_url: str | None = None
    no_verify_ssl: bool = False
    debug: bool = False


def agent_arguments(params, host_config: HostConfig):
    """
    Build Special Agent Command Line
    """
    args: list[str] = [
        "--host-name", host_config.name,
    ]

    if params.proxy_url:
        args.extend(["--proxy-url", params.proxy_url])

    if params.no_verify_ssl:
        args.append("--no-verify-ssl")

    if params.debug:
        args.append("--debug")

    yield SpecialAgentCommand(command_arguments=args)


special_agent_adfs_certificates = SpecialAgentConfig(
    name="adfs_certificates",
    parameter_parser=ConfigParser.model_validate,
    commands_function=agent_arguments,
)
