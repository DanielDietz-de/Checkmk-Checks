#!/usr/bin/env python3
"""Register S2D/HCI free-space thresholds and the shared operational-state policy consumed by storage and cluster checks."""

from __future__ import annotations

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    SimpleLevels,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _severity_choice(title: str, default: str) -> SingleChoice:
    """Build the common OK/WARN/CRIT/UNKNOWN selector used by every configurable S2D/HCI operational-state mapping."""

    return SingleChoice(
        title=Title(title),
        elements=(
            SingleChoiceElement(name="ok", title=Title("OK")),
            SingleChoiceElement(name="warn", title=Title("WARN")),
            SingleChoiceElement(name="crit", title=Title("CRIT")),
            SingleChoiceElement(name="unknown", title=Title("UNKNOWN")),
        ),
        prefill=DefaultValue(default),
    )


def _state_policy_elements() -> dict[str, DictElement]:
    """Return reusable operational-state policy elements with conservative defaults."""

    return {
        "degraded_state": DictElement(parameter_form=_severity_choice("Degraded or warning state", "warn"), required=True),
        "paused_state": DictElement(parameter_form=_severity_choice("Paused or suspended state", "warn"), required=True),
        "draining_state": DictElement(parameter_form=_severity_choice("Draining or resynchronizing state", "warn"), required=True),
        "offline_state": DictElement(parameter_form=_severity_choice("Offline, failed, or critical state", "crit"), required=True),
        "unknown_state": DictElement(parameter_form=_severity_choice("Unknown or unrecognized state", "unknown"), required=True),
    }


def _state_policy_form() -> Dictionary:
    """Return the generic operational-state mapping form used by multiple checks."""

    return Dictionary(
        title=Title("S2D/HCI operational state policy"),
        help_text=Help("Control how Microsoft operational states map to Checkmk service states. Unknown values default to UNKNOWN."),
        elements=_state_policy_elements(),
    )


def _free_space_form(title: str) -> Dictionary:
    """Return lower free-space thresholds plus the shared operational-state policy."""

    elements = _state_policy_elements()
    elements["levels_lower_free"] = DictElement(
        parameter_form=SimpleLevels(
            title=Title("Free space percentage"),
            help_text=Help("Warn or alert when free space falls below these percentages."),
            level_direction=LevelDirection.LOWER,
            form_spec_template=Float(),
            prefill_fixed_levels=DefaultValue(value=(15.0, 10.0)),
        ),
        required=True,
    )
    return Dictionary(title=Title(title), elements=elements)


def _csv_parameter_form() -> Dictionary:
    """Build Cluster Shared Volume free-space thresholds together with the complete shared operational-state policy."""

    return _free_space_form("S2D/HCI CSV thresholds")


def _volume_parameter_form() -> Dictionary:
    """Build volume free-space thresholds together with every required operational-state mapping consumed by the check."""

    return _free_space_form("S2D/HCI volume thresholds")


rule_spec_s2d_hci_state_policy = CheckParameters(
    name="s2d_hci_state_policy",
    title=Title("S2D/HCI operational state policy"),
    topic=Topic.APPLICATIONS,
    condition=HostAndItemCondition(item_title=Title("S2D/HCI object")),
    parameter_form=_state_policy_form,
)

rule_spec_s2d_hci_csv = CheckParameters(
    name="s2d_hci_csv",
    title=Title("S2D/HCI CSV free space"),
    topic=Topic.STORAGE,
    condition=HostAndItemCondition(item_title=Title("CSV identity")),
    parameter_form=_csv_parameter_form,
)

rule_spec_s2d_hci_volumes = CheckParameters(
    name="s2d_hci_volumes",
    title=Title("S2D/HCI volume free space"),
    topic=Topic.STORAGE,
    condition=HostAndItemCondition(item_title=Title("Volume identity")),
    parameter_form=_volume_parameter_form,
)
