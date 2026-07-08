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
    Float,
    LevelDirection,
    LevelsType,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _formspec_palo_alto_dos_zone_red():
    return Dictionary(
        title=Title("Palo Alto DoS Zone RED Drops"),
        help_text=Help(
            "Upper levels for the packet drop rates of the DoS protection zone "
            "RED action (activate / maximum), evaluated as packets per second."
        ),
        elements={
            "levels_activate": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Activate drop rate"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="pkts/s"),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((1000.0, 5000.0)),
                ),
            ),
            "levels_maximum": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Maximum drop rate"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="pkts/s"),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((1000.0, 5000.0)),
                ),
            ),
        },
    )


rule_spec_palo_alto_dos_zone_red = CheckParameters(
    name="palo_alto_dos_zone_red",
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=_formspec_palo_alto_dos_zone_red,
    title=Title("Palo Alto DoS Zone RED Drops"),
)
