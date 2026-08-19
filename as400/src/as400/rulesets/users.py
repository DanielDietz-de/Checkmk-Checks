#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from cmk.rulesets.v1 import (
        Title,
)

from cmk.rulesets.v1.form_specs import (
        Dictionary,
        DictElement,
        SimpleLevels,
        Integer,
        LevelDirection,
        InputHint,
)

from cmk.rulesets.v1.rule_specs import (
        CheckParameters,
        HostCondition,
        Topic,
)


def as400_users():
    """Handle as400 users for this module's workflow."""
    return Dictionary(
        elements={
            "user_levels": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Users"),
                    form_spec_template=Integer(unit_symbol="Users"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint(value=(9000, 9500)),
                )
            ),
        }
    )


rule_spec_as400_users = CheckParameters(
    name="as400_users",
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=as400_users,
    title=Title("AS400 Users"),
)
