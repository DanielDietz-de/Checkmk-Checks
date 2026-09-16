#!/usr/bin/env python3
"""Server-side command construction for Synology Active Backup for Microsoft 365."""

from collections.abc import Iterable, Mapping

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig, noop_parser


def _bounded_number(params: Mapping[str, object], key: str, minimum: float, maximum: float) -> str:
    if key not in params:
        raise ValueError(f"Missing required parameter: {key}")
    value = str(params[key]).strip()
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"Parameter {key} must be numeric") from exc
    if not minimum <= number <= maximum:
        raise ValueError(f"Parameter {key} must be between {minimum} and {maximum}")
    return value


def _agent_arguments(
    params: Mapping[str, object], host_config: HostConfig
) -> Iterable[SpecialAgentCommand]:
    del host_config

    api_host = str(params.get("api_host", "")).strip()
    if not api_host:
        raise ValueError("Missing required parameter: api_host")

    api_port = _bounded_number(params, "api_port", 1, 65535)
    timeout = _bounded_number(params, "timeout", 0.1, 120)
    api_token = params.get("api_token")
    if api_token is None:
        raise ValueError("Missing required parameter: api_token")

    yield SpecialAgentCommand(
        command_arguments=[
            "--host",
            api_host,
            "--port",
            api_port,
            "--timeout",
            timeout,
            "--token-id",
            api_token,
        ]
    )


special_agent_synology_active_backup_m365 = SpecialAgentConfig(
    name="synology_active_backup_m365",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
