#!/usr/bin/env python3
"""Server-side command wiring for Agent JSON."""

from typing import List, Optional

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class AgentJSONEndpoint(BaseModel):
    api_url: str
    username: Optional[str] = None
    password: Optional[Secret] = None
    method: Optional[str] = "post"


class AgentJSONParams(BaseModel):
    endpoints: Optional[List[AgentJSONEndpoint]] = None
    api_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[Secret] = None
    method: Optional[str] = "post"


def _endpoints(params: AgentJSONParams):
    if params.endpoints:
        return params.endpoints
    if params.api_url:
        return [
            AgentJSONEndpoint(
                api_url=params.api_url,
                username=params.username,
                password=params.password,
                method=params.method,
            )
        ]
    return []


def generate_agent_json_command(params: AgentJSONParams, host_config: HostConfig):
    arguments: list[str | Secret] = []
    for endpoint in _endpoints(params):
        arguments.extend(
            [
                endpoint.api_url,
                endpoint.username or "",
                endpoint.password if endpoint.password is not None else "",
                endpoint.method or "post",
            ]
        )

    yield SpecialAgentCommand(command_arguments=arguments)


special_agent_json = SpecialAgentConfig(
    name="json",
    parameter_parser=AgentJSONParams.model_validate,
    commands_function=generate_agent_json_command,
)
