#!/usr/bin/env python3
"""Register free-space threshold rules for S2D CSVs and volumes."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, Float, LevelDirection, SimpleLevels
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _free_space_parameter_form(title: str, help_text: str) -> Dictionary:
    """Build the shared lower free-space threshold form."""

    return Dictionary(
        title=Title(title),
        help_text=Help(help_text),
        elements={
            "levels_lower_free": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Free space percentage"),
                    help_text=Help("Warn or alert when free space percentage falls below these levels."),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=DefaultValue(value=(15.0, 10.0)),
                ),
                required=True,
            ),
        },
    )


def _csv_parameter_form() -> Dictionary:
    """Return the CSV free-space parameter form."""

    return _free_space_parameter_form(
        "S2D/HCI CSV thresholds",
        "Configure lower warning and critical thresholds for CSV free space percentage.",
    )


def _volume_parameter_form() -> Dictionary:
    """Return the volume free-space parameter form."""

    return _free_space_parameter_form(
        "S2D/HCI volume thresholds",
        "Configure lower warning and critical thresholds for volume free space percentage.",
    )


rule_spec_s2d_hci_csv = CheckParameters(
    name="s2d_hci_csv",
    title=Title("S2D/HCI CSV free space"),
    topic=Topic.STORAGE,
    condition=HostAndItemCondition(item_title=Title("CSV name")),
    parameter_form=_csv_parameter_form,
)


rule_spec_s2d_hci_volumes = CheckParameters(
    name="s2d_hci_volumes",
    title=Title("S2D/HCI volume free space"),
    topic=Topic.STORAGE,
    condition=HostAndItemCondition(item_title=Title("Volume name")),
    parameter_form=_volume_parameter_form,
)
