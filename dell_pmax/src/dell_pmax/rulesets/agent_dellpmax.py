#!/usr/bin/env python3
"""Ruleset for the Dell EMC PowerMax special agent."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, Password, String
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form_dell_powermax() -> Dictionary:
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
        },
    )


rule_spec_dellpmax_agent = SpecialAgent(
    name="dellpmax",
    topic=Topic.STORAGE,
    parameter_form=_parameter_form_dell_powermax,
    title=Title("Dell PowerMax"),
)
