#!/usr/bin/env python3
"""
Hitachi HNAS Snapshots Ruleset

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
    SimpleLevels,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

_TIME_MAGNITUDES = (
    TimeMagnitude.DAY,
    TimeMagnitude.HOUR,
    TimeMagnitude.MINUTE,
)


def _parameter_valuespec_hitachi_hnas_rest_snapshots():
    return Dictionary(
        elements={
            "levels_count": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Levels for number of snapshots"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue((50, 100)),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                ),
                required=False,
            ),
            "levels_age_oldest": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Levels for age of oldest snapshot"),
                    help_text=Help(
                        "Alert if the oldest snapshot of a filesystem is older "
                        "than the given age. Useful to detect forgotten "
                        "snapshots which consume space."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(displayed_magnitudes=_TIME_MAGNITUDES),
                    prefill_fixed_levels=DefaultValue((30.0 * 86400, 60.0 * 86400)),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                ),
                required=False,
            ),
            "levels_age_newest": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Levels for time since last snapshot"),
                    help_text=Help(
                        "Alert if the newest snapshot of a filesystem is older "
                        "than the given age. Useful to detect that snapshot "
                        "creation has stopped working."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(displayed_magnitudes=_TIME_MAGNITUDES),
                    prefill_fixed_levels=DefaultValue((2.0 * 86400, 3.0 * 86400)),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                ),
                required=False,
            ),
        }
    )


rule_spec_hitachi_hnas_rest_snapshots = CheckParameters(
    name="hitachi_hnas_rest_snapshots",
    topic=Topic.STORAGE,
    condition=HostAndItemCondition(
        item_title=Title("Filesystem"),
        item_form=String(),
    ),
    parameter_form=_parameter_valuespec_hitachi_hnas_rest_snapshots,
    title=Title("Hitachi HNAS Snapshots"),
)
