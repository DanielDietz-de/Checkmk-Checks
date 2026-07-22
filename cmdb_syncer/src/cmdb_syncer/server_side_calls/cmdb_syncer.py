#!/usr/bin/env python3
"""Server-side command wiring for CMDB Syncer monitoring."""

from collections.abc import Sequence

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class CMDBSyncerParams(BaseModel):
    api_url: str
    username: str
    password: Secret
    timeout: str
    services: Sequence[str] = Field(default_factory=list)
    fetch_cron: bool


def generate_cmdbsyncer_command(params: CMDBSyncerParams, host_config: HostConfig):
    args: list[str | Secret] = [
        "--api_url",
        params.api_url,
        "--username",
        params.username,
        "--password",
        params.password,
        "--timeout",
        params.timeout,
        "--services",
        ";".join(params.services),
        "--fetch_cron",
        str(params.fetch_cron),
    ]
    yield SpecialAgentCommand(command_arguments=args)


special_agent_CMDBSyncer = SpecialAgentConfig(
    name="cmdb_syncer",
    parameter_parser=CMDBSyncerParams.model_validate,
    commands_function=generate_cmdbsyncer_command,
)
