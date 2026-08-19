"""Rulesets API V1 forms for Aruba Central monitoring thresholds."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    Integer,
    LevelDirection,
    SimpleLevels,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, HostCondition, Topic


def _state_help() -> Help:
    """Handle state help for this module's workflow."""
    return Help("State mapping: 0=OK, 1=WARN, 2=CRIT, 3=UNKNOWN.")


def _summary_form() -> Dictionary:
    """Handle summary form for this module's workflow."""
    return Dictionary(
        elements={
            "api_rate_remaining_lower": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Lower levels for remaining API calls"),
                    form_spec_template=Float(unit_symbol="calls"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue(value=(500.0, 100.0)),
                ),
                required=True,
            ),
            "last_success_age_upper": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for last successful collection age"),
                    help_text=Help("Used when the collector serves last-known-good data after a cencli failure."),
                    form_spec_template=Float(unit_symbol="s"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(600.0, 1800.0)),
                ),
                required=True,
            ),
            "ap_down_upper": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for APs not Up"),
                    form_spec_template=Float(unit_symbol="APs"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(1.0, 5.0)),
                ),
                required=True,
            ),
        }
    )


def _ap_form() -> Dictionary:
    """Handle ap form for this module's workflow."""
    return Dictionary(
        elements={
            "status_down_state": DictElement(
                parameter_form=Integer(title=Title("State when AP status is not Up"), help_text=_state_help(), prefill=DefaultValue(2)),
                required=True,
            ),
            "sleep_state": DictElement(
                parameter_form=Integer(title=Title("State when AP sleep status is active"), help_text=_state_help(), prefill=DefaultValue(1)),
                required=True,
            ),
            "cpu_percent_upper": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for CPU utilization"),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(80.0, 90.0)),
                ),
                required=True,
            ),
            "mem_free_percent_lower": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Lower levels for free memory"),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue(value=(20.0, 10.0)),
                ),
                required=True,
            ),
            "clients_upper": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Optional upper levels for connected clients"),
                    form_spec_template=Float(unit_symbol="clients"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(60.0, 80.0)),
                ),
                required=False,
            ),
            "expected_firmware_regex": DictElement(
                parameter_form=String(
                    title=Title("Expected firmware regular expression"),
                    help_text=Help("Leave empty to disable firmware-compliance checking."),
                    prefill=DefaultValue(""),
                ),
                required=False,
            ),
        }
    )


def _radio_form() -> Dictionary:
    """Handle radio form for this module's workflow."""
    return Dictionary(
        elements={
            "status_down_state": DictElement(
                parameter_form=Integer(title=Title("State when radio status is not Up"), help_text=_state_help(), prefill=DefaultValue(2)),
                required=True,
            ),
            "utilization_upper": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for radio utilization"),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(75.0, 90.0)),
                ),
                required=True,
            ),
        }
    )


rule_spec_aruba_central_summary = CheckParameters(
    name="aruba_central_summary",
    title=Title("Aruba Central summary"),
    topic=Topic.GENERAL,
    parameter_form=_summary_form,
    condition=HostCondition(),
)

rule_spec_aruba_central_ap = CheckParameters(
    name="aruba_central_ap",
    title=Title("Aruba Central access point"),
    topic=Topic.GENERAL,
    parameter_form=_ap_form,
    condition=HostCondition(),
)

rule_spec_aruba_central_radio = CheckParameters(
    name="aruba_central_radio",
    title=Title("Aruba Central radio"),
    topic=Topic.GENERAL,
    parameter_form=_radio_form,
    condition=HostAndItemCondition(item_title=Title("Radio")),
)
