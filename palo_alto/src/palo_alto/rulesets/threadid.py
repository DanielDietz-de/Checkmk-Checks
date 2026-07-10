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
    LevelDirection,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _formspec_palo_alto_threadid():
    return Dictionary(
        title=Title("Age for Threat database updates"),
        help_text=Help(
            "Please configure levels for the maximum age of the last Threat "
            "(Threat ID) database update."
        ),
        elements={
            "age": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Age for Threat database updates"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.DAY, TimeMagnitude.HOUR],
                    ),
                    prefill_fixed_levels=DefaultValue((86400, 104400)),
                ),
            ),
        },
    )


rule_spec_palo_alto_threadid = CheckParameters(
    name="palo_alto_threadid",
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=_formspec_palo_alto_threadid,
    title=Title("Palo Alto Threat database age"),
)
