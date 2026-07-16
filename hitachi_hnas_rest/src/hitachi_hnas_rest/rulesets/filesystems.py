#!/usr/bin/env python3
"""
Hitachi HNAS Filesystems Ruleset

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
    Percentage,
    ServiceState,
    SimpleLevels,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_valuespec_hitachi_hnas_rest_filesystems():
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
            "state_not_mounted": DictElement(
                parameter_form=ServiceState(
                    title=Title("State if filesystem is not mounted"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
                required=False,
            ),
            "state_tp_invalid": DictElement(
                parameter_form=ServiceState(
                    title=Title("State if thin provisioning is enabled but not valid"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
                required=False,
            ),
            "state_tp_disabled": DictElement(
                parameter_form=ServiceState(
                    title=Title("State if thin provisioning is not enabled"),
                    help_text=Help(
                        "Set this to WARN or CRIT if all filesystems are "
                        "required to use thin provisioning."
                    ),
                    prefill=DefaultValue(ServiceState.OK),
                ),
                required=False,
            ),
        }
    )


rule_spec_hitachi_hnas_rest_filesystems = CheckParameters(
    name="hitachi_hnas_rest_filesystems",
    topic=Topic.STORAGE,
    condition=HostAndItemCondition(
        item_title=Title("Filesystem"),
        item_form=String(),
    ),
    parameter_form=_parameter_valuespec_hitachi_hnas_rest_filesystems,
    title=Title("Hitachi HNAS Filesystems"),
)
