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
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.rule_specs import NotificationParameters, Topic


def _parameters_redis_service():
    return Dictionary(
        title=Title("Create notification with the following parameters"),
        help_text=Help(
            "The notification reads the local site's automation secret. The configured target "
            "must therefore be this same site on localhost or another loopback address."
        ),
        elements={
            "proto": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    help_text=Help("Protocol used for the local Checkmk REST API."),
                    elements=[
                        SingleChoiceElement(name="http", title=Title("HTTP")),
                        SingleChoiceElement(name="https", title=Title("HTTPS")),
                    ],
                    prefill=DefaultValue("http"),
                ),
                required=True,
            ),
            "hostname": DictElement(
                parameter_form=String(
                    title=Title("Local hostname"),
                    help_text=Help(
                        "Use localhost or a loopback address. Remote hostnames are rejected before "
                        "the automation secret is read."
                    ),
                    field_size=40,
                ),
                required=True,
            ),
            "sitename": DictElement(
                parameter_form=String(
                    title=Title("Local site name"),
                    help_text=Help("Must match the site executing the notification."),
                    field_size=40,
                ),
                required=True,
            ),
        },
    )


rule_spec_redis_service = NotificationParameters(
    title=Title("Rediscover service"),
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_parameters_redis_service,
    name="rediscover_service",
)
