#!/usr/bin/env python3
"""Ruleset for the hardened Agent JSON special agent."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    List,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _migrate(value):
    if "endpoints" in value:
        return value
    endpoint = {}
    for key in ("api_url", "method", "username", "password"):
        if key in value:
            endpoint[key] = value[key]
    return {"endpoints": [endpoint]} if endpoint else value


def _endpoint_form():
    return Dictionary(
        title=Title("HTTPS endpoint"),
        help_text=Help(
            "The endpoint must be an absolute HTTPS URL. Redirects, embedded "
            "credentials and cleartext HTTP are rejected by the runtime."
        ),
        elements={
            "api_url": DictElement(
                parameter_form=String(
                    title=Title("HTTPS API URL"),
                    help_text=Help(
                        "Absolute HTTPS URL. TLS certificates are verified "
                        "against the Checkmk server's system trust store."
                    ),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "method": DictElement(
                parameter_form=SingleChoice(
                    title=Title("HTTP method"),
                    help_text=Help(
                        "Only GET and POST are accepted. POST remains the "
                        "default for compatibility with existing rules."
                    ),
                    elements=(
                        SingleChoiceElement(name="post", title=Title("POST")),
                        SingleChoiceElement(name="get", title=Title("GET")),
                    ),
                    prefill=DefaultValue("post"),
                ),
                required=False,
            ),
            "username": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help("Optional HTTP Basic authentication user."),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=False,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Password"),
                    help_text=Help(
                        "Optional HTTP Basic authentication password stored as "
                        "a Checkmk secret."
                    ),
                ),
                required=False,
            ),
        },
    )


def _parameter_form_special_agent_json():
    return Dictionary(
        title=Title("Agent JSON"),
        help_text=Help(
            "Fetch bounded, validated health JSON over verified HTTPS and "
            "convert it to escaped Checkmk local checks."
        ),
        migrate=_migrate,
        elements={
            "endpoints": DictElement(
                parameter_form=List(
                    title=Title("Endpoints"),
                    help_text=Help(
                        "Each endpoint has independent credentials and method. "
                        "All returned checks are merged into one local section."
                    ),
                    element_template=_endpoint_form(),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            )
        },
    )


rule_spec_agent_json = SpecialAgent(
    name="json",
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_parameter_form_special_agent_json,
    title=Title("Agent JSON"),
)
