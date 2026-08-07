#!/usr/bin/env python3
"""Register CPU, memory-pressure, and checkpoint-age workload rules."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, Float, LevelDirection, SimpleLevels
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _workload_parameter_form() -> Dictionary:
    """Return the workload CPU and memory-pressure parameter form."""

    return Dictionary(
        title=Title("S2D/HCI workload thresholds"),
        help_text=Help("Configure upper CPU and memory pressure thresholds for monitored workloads."),
        elements={
            "levels_upper_cpu": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("CPU usage percentage"),
                    help_text=Help("Warn or alert when workload CPU usage is above these levels."),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=DefaultValue(value=(80.0, 95.0)),
                ),
                required=True,
            ),
            "levels_upper_memory_pressure": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Memory pressure percentage"),
                    help_text=Help("Warn or alert when workload memory pressure is above these levels."),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=DefaultValue(value=(100.0, 120.0)),
                ),
                required=True,
            ),
        },
    )


def _retained_point_parameter_form() -> Dictionary:
    """Return the retained recovery-point age parameter form."""

    return Dictionary(
        title=Title("S2D/HCI retained recovery point thresholds"),
        help_text=Help("Configure upper age thresholds for retained workload recovery points."),
        elements={
            "levels_upper_age_hours": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Age in hours"),
                    help_text=Help("Warn or alert when retained recovery point age exceeds these levels."),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=DefaultValue(value=(24.0, 72.0)),
                ),
                required=True,
            ),
        },
    )


rule_spec_s2d_hci_virtualization_workloads = CheckParameters(
    name="s2d_hci_virtualization_workloads",
    title=Title("S2D/HCI workload CPU and memory"),
    topic=Topic.STORAGE,
    condition=HostAndItemCondition(item_title=Title("Workload name")),
    parameter_form=_workload_parameter_form,
)


rule_spec_s2d_hci_virtualization_checkpoints = CheckParameters(
    name="s2d_hci_virtualization_checkpoints",
    title=Title("S2D/HCI retained recovery point age"),
    topic=Topic.STORAGE,
    condition=HostAndItemCondition(item_title=Title("Recovery point name")),
    parameter_form=_retained_point_parameter_form,
)
