#!/usr/bin/env python3
"""Register Hyper-V workload and checkpoint threshold rules for S2D/HCI."""

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


def _upper_levels(title: str, warn: float, crit: float) -> SimpleLevels:
    """Return a reusable upper-threshold form with a valid Checkmk default wrapper."""

    return SimpleLevels(
        title=Title(title),
        level_direction=LevelDirection.UPPER,
        form_spec_template=Float(),
        prefill_fixed_levels=DefaultValue(value=(warn, crit)),
    )


def _severity_choice(title: str, default: str) -> SingleChoice:
    """Return a Checkmk state selector shared by VM operational-state policy fields."""

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


def _workload_state_elements() -> dict[str, DictElement]:
    """Return every operational-state mapping consumed by virtualization checks."""

    return {
        "degraded_state": DictElement(
            parameter_form=_severity_choice("Degraded or warning state", "warn"),
            required=True,
        ),
        "paused_state": DictElement(
            parameter_form=_severity_choice("Paused or suspended state", "warn"),
            required=True,
        ),
        "draining_state": DictElement(
            parameter_form=_severity_choice("Draining or resynchronizing state", "warn"),
            required=True,
        ),
        "offline_state": DictElement(
            parameter_form=_severity_choice("Offline, failed, or critical state", "crit"),
            required=True,
        ),
        "unknown_state": DictElement(
            parameter_form=_severity_choice("Unknown or unrecognized state", "unknown"),
            required=True,
        ),
    }


def _workload_form() -> Dictionary:
    """Return CPU, memory-pressure, and operational-state settings for opt-in VMs."""

    elements = _workload_state_elements()
    elements.update(
        {
            "levels_upper_cpu": DictElement(
                parameter_form=_upper_levels("CPU usage", 80.0, 95.0),
                required=True,
            ),
            "levels_upper_memory_pressure": DictElement(
                parameter_form=_upper_levels("Memory pressure", 100.0, 120.0),
                required=True,
            ),
        }
    )
    return Dictionary(
        title=Title("S2D/HCI virtualization workload thresholds"),
        help_text=Help(
            "Applied only when custom Hyper-V workload monitoring is explicitly enabled. "
            "The state controls match every state-policy default consumed by the check."
        ),
        elements=elements,
    )


def _checkpoint_form() -> Dictionary:
    """Return retained checkpoint age plus the full operational-state policy."""

    elements = _workload_state_elements()
    elements["levels_upper_age_hours"] = DictElement(
        parameter_form=_upper_levels("Checkpoint age in hours", 24.0, 72.0),
        required=True,
    )
    return Dictionary(
        title=Title("S2D/HCI checkpoint age thresholds"),
        help_text=Help(
            "Configure retained checkpoint age and every operational-state mapping "
            "accepted by the checkpoint check defaults."
        ),
        elements=elements,
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
