"""
UCP / MKE Health Special Agent - Server Side Calls

Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""
from pydantic import BaseModel
from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig


class NodeConfig(BaseModel):
    """
    A single node: piggyback host name and its _ping URL.
    """
    name: str
    url: str


class CollectionConfig(BaseModel):
    """Represent collectionconfig behavior and associated state."""
    service_name: str = "UCP Manager"
    warn_unhealthy: int | None = None
    crit_unhealthy: int = 2


class ConfigParser(BaseModel):
    """Represent configparser behavior and associated state."""
    nodes: list[NodeConfig] = []
    service_name: str = "UCP Healthy"
    piggyback: bool = False
    collection: CollectionConfig | None = None
    timeout: int = 10
    no_verify_ssl: bool = False
    client_cert: str | None = None
    client_key: str | None = None


def agent_arguments(params: ConfigParser, host_config: HostConfig):
    """
    Build Special Agent Command Line
    """
    args: list[str] = []

    for node in params.nodes:
        args.extend(["--node", node.name, node.url])

    args.extend(["--service-name", params.service_name])
    args.extend(["--timeout", str(params.timeout)])

    if params.piggyback:
        args.append("--piggyback")

    if params.collection is not None:
        args.append("--collection")
        args.extend(["--collection-service-name", params.collection.service_name])
        args.extend(["--crit-unhealthy", str(params.collection.crit_unhealthy)])
        if params.collection.warn_unhealthy is not None:
            args.extend(["--warn-unhealthy", str(params.collection.warn_unhealthy)])

    if params.no_verify_ssl:
        args.append("--no-verify-ssl")

    if params.client_cert:
        args.extend(["--client-cert", params.client_cert])
    if params.client_key:
        args.extend(["--client-key", params.client_key])

    yield SpecialAgentCommand(command_arguments=args)


special_agent_ucp_health = SpecialAgentConfig(
    name="ucp_health",
    parameter_parser=ConfigParser.model_validate,
    commands_function=agent_arguments,
)
