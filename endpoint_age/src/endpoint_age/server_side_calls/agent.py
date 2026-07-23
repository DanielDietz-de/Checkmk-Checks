import json

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig


class Endpoint(BaseModel):
    name: str
    url: str
    source: tuple[str, str | None]
    timeout: float | None = Field(default=None, ge=0.5, le=60)


class ConfigParser(BaseModel):
    endpoints: list[Endpoint] = Field(min_length=1, max_length=100)


def _source_to_str(source: tuple[str, str | None]) -> str:
    kind, value = source
    if kind == "age_header":
        return "age_header"
    if kind == "date_header":
        return f"date_header:{value or 'Last-Modified'}"
    if kind == "json_path":
        return f"json_path:{value or ''}"
    return kind


def agent_arguments(params: ConfigParser, host_config: HostConfig):
    args: list[str] = []
    for endpoint in params.endpoints:
        payload = {
            "name": endpoint.name,
            "url": endpoint.url,
            "source": _source_to_str(endpoint.source),
        }
        if endpoint.timeout is not None:
            payload["timeout"] = endpoint.timeout
        args.extend(("--endpoint", json.dumps(payload, sort_keys=True)))
    yield SpecialAgentCommand(command_arguments=args)


special_agent_endpoint_age = SpecialAgentConfig(
    name="endpoint_age",
    parameter_parser=ConfigParser.model_validate,
    commands_function=agent_arguments,
)
