"""Server-side command wiring for Hitachi HNAS REST monitoring."""

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
    noop_parser,
)


def _agent_arguments(params, host_config: HostConfig):
    address_mode, address_value = params["address"]
    if address_mode == "ip":
        address = host_config.primary_ip_config.address
    elif address_mode == "custom":
        address = address_value
    else:
        address = host_config.name

    args: list[str | Secret] = [
        "--host-address",
        address,
        "--port",
        str(params.get("port", 8444)),
        "--timeout",
        str(params.get("timeout", 30)),
    ]

    auth_method, auth = params["auth"]
    if auth_method == "api_key":
        args.extend(("--api-key", auth["key"]))
    else:
        args.extend(
            (
                "--user",
                auth["username"],
                "--password",
                auth["password"],
            )
        )

    if params.get("no_cert_check"):
        args.append("--no-cert-check")

    yield SpecialAgentCommand(command_arguments=args)


special_agent_hitachi_hnas_rest = SpecialAgentConfig(
    name="hitachi_hnas_rest",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
