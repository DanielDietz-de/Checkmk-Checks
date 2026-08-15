#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    BooleanChoice,
    Float,
    InputHint,
    Password,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import (
    SpecialAgent,
    Topic,
)


def _valuespec_special_agent_pure():
    """Handle valuespec special agent pure for this module's workflow."""
    return Dictionary(
        title = Title("Pure via WebAPI"),
        help_text = Help("This rule set selects the special agent for Pure"),
        elements = {
            "token": DictElement(
                parameter_form = Password(
                    title = Title("Web API Token"),
                    custom_validate = (LengthInRange(min_value=1),),
                ),
                required = True,
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

rule_spec_pure = SpecialAgent(
    name = "pure",
    topic = Topic.STORAGE,
    parameter_form = _valuespec_special_agent_pure,
    title = Title("Pure via WebAPI"),
)
