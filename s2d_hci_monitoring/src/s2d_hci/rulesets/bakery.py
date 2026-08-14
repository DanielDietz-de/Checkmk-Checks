#!/usr/bin/env python3
"""Agent Bakery rule for bounded S2D/HCI Windows collector deployment."""

from __future__ import annotations

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import BooleanChoice, DefaultValue, DictElement, Dictionary, Integer, SingleChoice, SingleChoiceElement
from cmk.rulesets.v1.form_specs.validators import NumberInRange
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _collector_toggle(title: str, default: bool) -> BooleanChoice:
    """Return a documented Boolean deployment toggle for one collector class."""

    return BooleanChoice(title=Title(title), prefill=DefaultValue(default))


def _integer_setting(title: str, default: int, minimum: int, maximum: int) -> Integer:
    """Return one bounded integer field shared by Bakery and collector validation."""

    return Integer(
        title=Title(title),
        prefill=DefaultValue(default),
        custom_validate=(NumberInRange(min_value=minimum, max_value=maximum),),
    )


def _s2d_hci_bakery_form() -> Dictionary:
    """Build the Agent Bakery form that controls collector deployment mode, hard safety limits, and privacy-minimizing field inclusion."""

    return Dictionary(
        title=Title("S2D/HCI monitoring collectors"),
        help_text=Help(
            "Deploy read-only S2D/HCI collectors to Windows cluster nodes. "
            "Hyper-V workload collection is opt-in to avoid overlapping native Checkmk monitoring."
        ),
        elements={
            "fast_enabled": DictElement(parameter_form=_collector_toggle("Deploy fast cluster collector", True), required=True),
            "storage_enabled": DictElement(parameter_form=_collector_toggle("Deploy storage collector", True), required=True),
            "jobs_enabled": DictElement(parameter_form=_collector_toggle("Deploy storage-jobs collector", True), required=True),
            "health_enabled": DictElement(parameter_form=_collector_toggle("Deploy S2D health collector", True), required=True),
            "virtualization_mode": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Custom Hyper-V workload collection"),
                    help_text=Help("Disabled by default. Direct and gMSA spool modes are mutually exclusive."),
                    elements=(
                        SingleChoiceElement(name="disabled", title=Title("Disabled")),
                        SingleChoiceElement(name="direct", title=Title("Direct Checkmk agent plug-in")),
                        SingleChoiceElement(name="gmsa_spool", title=Title("Dedicated gMSA spool task")),
                    ),
                    prefill=DefaultValue("disabled"),
                ),
                required=True,
            ),
            "max_records": DictElement(parameter_form=_integer_setting("Maximum records per collector run", 2000, 1, 5000), required=True),
            "max_output_bytes": DictElement(parameter_form=_integer_setting("Maximum collector output bytes", 1048576, 16384, 4194304), required=True),
            "max_runtime_seconds": DictElement(parameter_form=_integer_setting("Maximum collector runtime seconds", 120, 5, 240), required=True),
            "include_addresses": DictElement(parameter_form=_collector_toggle("Include network addresses", False), required=True),
            "include_paths": DictElement(parameter_form=_collector_toggle("Include filesystem and VHD paths", False), required=True),
            "include_serials": DictElement(parameter_form=_collector_toggle("Include physical-disk serials and unique IDs", False), required=True),
            "include_locations": DictElement(parameter_form=_collector_toggle("Include physical hardware locations", False), required=True),
        },
    )


rule_spec_s2d_hci_agent = AgentConfig(
    name="s2d_hci",
    title=Title("S2D/HCI monitoring collectors"),
    topic=Topic.APPLICATIONS,
    parameter_form=_s2d_hci_bakery_form,
)
