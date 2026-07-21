from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig


class FeedEntry(BaseModel):
    name: str
    url: str


class ConfigParser(BaseModel):
    feeds: list[FeedEntry] = Field(min_length=1, max_length=100)
    timeout: float | None = Field(default=None, ge=0.5, le=60)
    user_agent: str | None = None


def agent_arguments(params: ConfigParser, host_config: HostConfig):
    args: list[str] = []
    if params.timeout is not None:
        args.extend(("--timeout", str(params.timeout)))
    if params.user_agent:
        args.extend(("--user-agent", params.user_agent))
    for feed in params.feeds:
        args.extend(("--feed", f"{feed.name}={feed.url}"))
    yield SpecialAgentCommand(command_arguments=args)


special_agent_status_feed = SpecialAgentConfig(
    name="status_feed",
    parameter_parser=ConfigParser.model_validate,
    commands_function=agent_arguments,
)
