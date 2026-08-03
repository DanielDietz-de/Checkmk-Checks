#!/usr/bin/env python3
"""Ruleset for the CSMON special agent."""

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, Password, String
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _form_special_agents_csmon() -> Dictionary:
    return Dictionary(
        title=Title("CSMON Connection"),
        elements={
            "username": DictElement(
                required=True,
                parameter_form=String(title=Title("Username")),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(title=Title("Password")),
            ),
        },
    )


rule_spec_csmon = SpecialAgent(
    topic=Topic.APPLICATIONS,
    name="csmon",
    title=Title("CSMON Connector"),
    parameter_form=_form_special_agents_csmon,
)
