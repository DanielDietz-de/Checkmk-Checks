#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    Dictionary,
    DictElement,
    InputHint,
    Integer,
    LevelDirection,
    Password,
    SimpleLevels,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostCondition,
    SpecialAgent,
    Topic,
)


def _parameter_semu_frames() -> Dictionary:
    """Define service-level thresholds for the SEMU frame rate."""
    return Dictionary(
        elements={
            "levels": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Framerate Levels"),
                    form_spec_template=Integer(unit_symbol="Frames/s"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=InputHint(value=(10, 5)),
                )
            ),
        }
    )


rule_spec_semu_frames = CheckParameters(
    name="semu_frames",
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=_parameter_semu_frames,
    title=Title("Semu Framerate"),
)


def _valuespec_special_agent_semu() -> Dictionary:
    """Define credentials and explicit TLS-verification controls."""
    return Dictionary(
        title=Title("SEMU Agent"),
        help_text=Help("This rule activates the special agent for SEMU."),
        elements={
            "username": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help("User for HTTP Basic authentication."),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Password"),
                    help_text=Help("Password of the SEMU API user."),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "ca_file": DictElement(
                parameter_form=String(
                    title=Title("Custom CA bundle"),
                    help_text=Help(
                        "Optional absolute path on the Checkmk server to a PEM CA "
                        "bundle used to verify a private or self-signed SEMU certificate."
                    ),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=False,
            ),
            "no_cert_check": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Disable TLS certificate verification"),
                    help_text=Help(
                        "Explicit compatibility option for exceptional temporary use. "
                        "Prefer a custom CA bundle and do not configure both options."
                    ),
                    prefill=DefaultValue(False),
                ),
                required=False,
            ),
        },
    )


rule_spec_semu_agent = SpecialAgent(
    name="semu",
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_special_agent_semu,
    title=Title("SEMU Framerate"),
)
