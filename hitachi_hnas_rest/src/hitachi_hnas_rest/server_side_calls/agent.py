"""
Hitachi HNAS REST API Special Agent

Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""
from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
    noop_parser,
)


def _agent_arguments(params, host_config: HostConfig):
    """
    Build Special Agent Command Line
    """
    args: list[str | Secret] = [
        "--host-address",
        params.get("hostaddress") or host_config.primary_ip_config.address,
        "--port", str(params.get("port", 8444)),
        "--timeout", str(params.get("timeout", 30)),
    ]

    auth_method, auth = params["auth"]
    if auth_method == "api_key":
        args += ["--api-key", auth["key"].unsafe()]
    else:
        args += [
            "--user", auth["username"],
            "--password", auth["password"].unsafe(),
        ]

    if params.get("no_cert_check"):
        args.append("--no-cert-check")

    yield SpecialAgentCommand(command_arguments=args)


special_agent_hitachi_hnas_rest = SpecialAgentConfig(
    name="hitachi_hnas_rest",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
