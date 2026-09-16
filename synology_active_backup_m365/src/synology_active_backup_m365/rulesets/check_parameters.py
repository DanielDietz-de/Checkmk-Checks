#!/usr/bin/env python3
"""Ruleset for Synology Active Backup for Microsoft 365 task thresholds."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "last_success_age_upper": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Maximum age of the last fully successful backup"),
                    help_text=Help(
                        "Age since the last run that the Synology collector classifies as fully successful. "
                        "Warning/partial runs do not reset this timer. The defaults assume a daily backup "
                        "schedule: WARN after 30 hours and CRIT after 48 hours."
                    ),
                    form_spec_template=Float(unit_symbol="s"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(108000.0, 172800.0)),
                ),
            ),
        }
    )


rule_spec_synology_active_backup_m365 = CheckParameters(
    name="synology_active_backup_m365",
    title=Title("Synology Active Backup for Microsoft 365"),
    topic=Topic.GENERAL,
    parameter_form=_parameter_form,
    condition=HostAndItemCondition(item_title=Title("Backup task ID")),
)
