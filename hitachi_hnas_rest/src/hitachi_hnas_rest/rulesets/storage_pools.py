#!/usr/bin/env python3
"""
Hitachi HNAS Storage Pools Ruleset

Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    Percentage,
    SimpleLevels,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_valuespec_hitachi_hnas_rest_storage_pools():
    return Dictionary(
        elements={
            "levels_used": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Levels for used space"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue((80.0, 90.0)),
                ),
                required=False,
            ),
        }
    )


rule_spec_hitachi_hnas_rest_storage_pools = CheckParameters(
    name="hitachi_hnas_rest_storage_pools",
    topic=Topic.STORAGE,
    condition=HostAndItemCondition(
        item_title=Title("Storage pool"),
        item_form=String(),
    ),
    parameter_form=_parameter_valuespec_hitachi_hnas_rest_storage_pools,
    title=Title("Hitachi HNAS Storage Pools"),
)
