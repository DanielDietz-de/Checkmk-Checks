#!/usr/bin/env python3
"""Register Hyper-V workload and checkpoint threshold rules for S2D/HCI."""

from __future__ import annotations

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, Float, LevelDirection, SimpleLevels
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _upper_levels(title: str, warn: float, crit: float) -> SimpleLevels:
    """Return a reusable upper-threshold form with a valid Checkmk default wrapper."""

    return SimpleLevels(
        title=Title(title),
        level_direction=LevelDirection.UPPER,
        form_spec_template=Float(),
        prefill_fixed_levels=DefaultValue(value=(warn, crit)),
    )


def _workload_form() -> Dictionary:
    """Return CPU and memory-pressure thresholds for opt-in VM workloads."""

    return Dictionary(
        title=Title("S2D/HCI virtualization workload thresholds"),
        help_text=Help("Applied only when custom Hyper-V workload monitoring is explicitly enabled."),
        elements={
            "levels_upper_cpu": DictElement(parameter_form=_upper_levels("CPU usage", 80.0, 95.0), required=True),
            "levels_upper_memory_pressure": DictElement(parameter_form=_upper_levels("Memory pressure", 100.0, 120.0), required=True),
        },
    )


def _checkpoint_form() -> Dictionary:
    """Return retained checkpoint age thresholds in hours."""

    return Dictionary(
        title=Title("S2D/HCI checkpoint age thresholds"),
        elements={
            "levels_upper_age_hours": DictElement(
                parameter_form=_upper_levels("Checkpoint age in hours", 24.0, 72.0),
                required=True,
            )
        },
    )


rule_spec_s2d_hci_virtualization_workloads = CheckParameters(
    name="s2d_hci_virtualization_workloads",
    title=Title("S2D/HCI virtualization workloads"),
    topic=Topic.APPLICATIONS,
    condition=HostAndItemCondition(item_title=Title("VM identity")),
    parameter_form=_workload_form,
)

rule_spec_s2d_hci_virtualization_checkpoints = CheckParameters(
    name="s2d_hci_virtualization_checkpoints",
    title=Title("S2D/HCI virtualization checkpoints"),
    topic=Topic.APPLICATIONS,
    condition=HostAndItemCondition(item_title=Title("Checkpoint identity")),
    parameter_form=_checkpoint_form,
)
