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
    Integer,
    LevelDirection,
    LevelsType,
    Percentage,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _formspec_palo_alto_sessions():
    return Dictionary(
        title=Title("Palo Alto Sessions"),
        help_text=Help(
            "Levels for the session table utilization and the number of active "
            "sessions of a Palo Alto firewall."
        ),
        elements={
            "levels_utilization": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Session table utilization"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue((80.0, 90.0)),
                ),
            ),
            "levels_active": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Active sessions"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="sessions"),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((1000000, 5000000)),
                ),
            ),
        },
    )


rule_spec_palo_alto_sessions = CheckParameters(
    name="palo_alto_sessions",
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=_formspec_palo_alto_sessions,
    title=Title("Palo Alto Sessions"),
)
