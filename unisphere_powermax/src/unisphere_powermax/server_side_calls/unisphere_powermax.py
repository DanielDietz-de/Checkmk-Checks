#!/usr/bin/env python3
"""Server-side command wiring for Unisphere PowerMax."""

from typing import Optional

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class AgentPowermaxUParams(BaseModel):
    username: str
    password: Secret
    port: Optional[int] = None
    api_version: Optional[int] = 100
    use_ip: Optional[bool] = None
    disable_get_srp_info: Optional[bool] = None
    disable_get_director_info: Optional[bool] = None
    disable_get_health_score_info: Optional[bool] = None
    disable_get_health_check_info: Optional[bool] = None
    disable_get_array_performance_info: Optional[bool] = None
    disable_get_port_group_info: Optional[bool] = None
    disable_get_alert_info: Optional[bool] = None
    disable_get_masking_view_info: Optional[bool] = None
    enable_remote_sym_checks: Optional[bool] = None
    cache_time: Optional[int] = None
    no_cert_check: Optional[bool] = None


def generate_powermanx_command(params: AgentPowermaxUParams, host_config: HostConfig):
    args: list[str | Secret] = [
        "--user",
        params.username,
        "--password",
        params.password,
    ]
    if params.port:
        args.extend(("--port", str(params.port)))
    if params.cache_time:
        args.extend(("--cache_time", str(params.cache_time)))
    args.extend(("--api_version", str(params.api_version)))
    for option in (
        "disable_get_srp_info",
        "disable_get_director_info",
        "disable_get_health_score_info",
        "disable_get_health_check_info",
        "disable_get_array_performance_info",
        "disable_get_port_group_info",
        "disable_get_alert_info",
        "disable_get_masking_view_info",
        "enable_remote_sym_checks",
        "no_cert_check",
    ):
        if getattr(params, option):
            args.append(f"--{option}")

    args.append("--hostname")
    if params.use_ip:
        try:
            ip_address = host_config.ipv4_address
        except AttributeError:
            ip_address = host_config.primary_ip_config.address
        args.append(ip_address)
    else:
        args.append(host_config.name)

    yield SpecialAgentCommand(command_arguments=args)


special_agent_semu = SpecialAgentConfig(
    name="unisphere_powermax",
    parameter_parser=AgentPowermaxUParams.model_validate,
    commands_function=generate_powermanx_command,
)
