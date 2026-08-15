#!/usr/bin/env python3
"""Ruleset for the Dell EMC PowerMax special agent."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import BooleanChoice, DictElement, Dictionary, Float, InputHint, Integer, Password, String
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form_dell_powermax() -> Dictionary:
    """Handle parameter form dell powermax for this module's workflow."""
    return Dictionary(
        title=Title("Check state of Dell EMC PowerMax storage pools"),
        help_text=Help(
            "Selects the <tt>dellpmax</tt> special agent and monitors Dell EMC "
            "PowerMax storage pools through the REST API. The API account requires "
            "only the monitoring role and read-only permissions."
        ),
        elements={
            "username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help("Read-only monitoring account on the storage system."),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password"),
                    help_text=Help("Password for the storage-system monitoring account."),
                ),
            ),
            "port": DictElement(
                parameter_form=Integer(title=Title("API port"), prefill=InputHint(8443)),
            ),
            "timeout": DictElement(
                parameter_form=Float(title=Title("Request timeout in seconds"), prefill=InputHint(30.0)),
            ),
            "ca_file": DictElement(
                parameter_form=String(title=Title("Private CA bundle path")),
            ),
            "no_cert_check": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Disable TLS certificate verification"),
                    help_text=Help("Use only as an explicit temporary compatibility exception."),
                ),
            ),
        },
    )


rule_spec_dellpmax_agent = SpecialAgent(
    name="dellpmax",
    topic=Topic.STORAGE,
    parameter_form=_parameter_form_dell_powermax,
    title=Title("Dell PowerMax"),
)
