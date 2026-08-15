#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from pydantic import BaseModel
from typing import Optional
from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
)


class VideotextParams(BaseModel):
    """Represent videotextparams behavior and associated state."""
    url: str
    pattern: str
    timeout: Optional[float] = None
    warn: Optional[float] = None
    crit: Optional[float] = None



def videotext_arguments(params, host_params):
    """Handle videotext arguments for this module's workflow."""
    yield ActiveCheckCommand(
        service_description = "Videotext",
        command_arguments = (
            "-u",
            params.url,
            "-p",
            params.pattern,
            "-t",
            str(params.timeout) if params.timeout else "2.5",
            "-w",
            str(params.warn) if params.warn else "900.0",
            "-c",
            str(params.crit) if params.crit else "1200.0",
        )
    )


active_check_videotext = ActiveCheckConfig(
    name = "videotext",
    parameter_parser = VideotextParams.model_validate,
    commands_function = videotext_arguments,
)
