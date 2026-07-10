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


def _formspec_palo_alto_urlfilter():
    return Dictionary(
        title=Title("Age for URL-Filtering database updates"),
        help_text=Help(
            "Please configure levels for the maximum age of the last "
            "URL-Filtering database update."
        ),
        elements={
            "age": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Age for URL-Filtering database updates"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.DAY, TimeMagnitude.HOUR],
                    ),
                    prefill_fixed_levels=DefaultValue((86400, 104400)),
                ),
            ),
        },
    )


rule_spec_palo_alto_urlfilter = CheckParameters(
    name="palo_alto_urlfilter",
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=_formspec_palo_alto_urlfilter,
    title=Title("Palo Alto URL-Filtering database age"),
)
