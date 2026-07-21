#!/usr/bin/env python3
"""Ruleset for the Dell EMC PowerMax special agent."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    Password,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NumberInRange
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _valuespec_special_agent_dell_powermax() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerMax via Unisphere REST API"),
        help_text=Help(
            "Uses verified HTTPS and a read-only monitoring account. The API "
            "version is configurable because Unisphere versions expose different "
            "REST namespaces."
        ),
        elements={
            "username": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help("Read-only Unisphere monitoring user."),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Password"),
                    help_text=Help("Password stored as a Checkmk secret."),
                ),
                required=True,
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("HTTPS port"),
                    prefill=DefaultValue(8443),
                    custom_validate=(NumberInRange(min_value=1, max_value=65535),),
                ),
                required=True,
            ),
            "api_version": DictElement(
                parameter_form=Integer(
                    title=Title("Unisphere REST API version"),
                    help_text=Help("For example 100. Consult the target Unisphere version."),
                    prefill=DefaultValue(100),
                    custom_validate=(NumberInRange(min_value=1, max_value=999),),
                ),
                required=True,
            ),
            "timeout": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Request timeout"),
                    displayed_magnitudes=(TimeMagnitude.SECOND,),
                    prefill=DefaultValue(15.0),
                ),
                required=True,
            ),
            "ca_bundle": DictElement(
                parameter_form=String(
                    title=Title("Private CA bundle"),
                    help_text=Help(
                        "Optional absolute path to a regular CA bundle file. "
                        "Leave empty to use the system trust store."
                    ),
                ),
                required=False,
            ),
        },
    )


rule_spec_semu_agent = SpecialAgent(
    name="agent_dellpmax",
    topic=Topic.STORAGE,
    parameter_form=_valuespec_special_agent_dell_powermax,
    title=Title("Dell PowerMax"),
)
