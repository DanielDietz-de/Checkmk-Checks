#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _valuespec_special_agent_notification_monitor():
    return Dictionary(
        title=Title("Notification monitor"),
        help_text=Help(
            "This special agent reads the local site's automation secret and therefore "
            "may only query the same Checkmk site through localhost or another loopback address."
        ),
        elements={
            "path": DictElement(
                parameter_form=String(
                    title=Title("Local Checkmk site URL"),
                    help_text=Help(
                        "URL of this local Checkmk site using localhost or a loopback address, "
                        "for example http://localhost/cmk/. Remote hosts are rejected before "
                        "the automation secret is read."
                    ),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "command_regex": DictElement(
                parameter_form=String(
                    title=Title("Regex to filter notification command"),
                    help_text=Help("Command names are shown in the Checkmk notification setup."),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "timeout": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Timeout"),
                    displayed_magnitudes=[TimeMagnitude.MILLISECOND, TimeMagnitude.SECOND],
                    prefill=DefaultValue(2.5),
                ),
                required=True,
            ),
        },
    )


rule_spec_service_counter = SpecialAgent(
    name="notification_monitor",
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_special_agent_notification_monitor,
    title=Title("Notification Monitor"),
)
