#!/usr/bin/env python3

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, String, validators
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _required_string(title: str, default: str, help_text: str | None = None) -> String:
    return String(
        title=Title(title),
        help_text=Help(help_text) if help_text else None,
        prefill=DefaultValue(default),
        custom_validate=(validators.LengthInRange(min_value=1),),
    )


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Switch port synchronization"),
        help_text=Help(
            "Compares already monitored Checkmk interface services on two switches. "
            "Apply one rule to both switch hosts. No additional SNMP polling is performed. "
            "At discovery, a port pair is selected when at least one member is confirmed up; "
            "ports down on both members are treated as unused."
        ),
        elements={
            "pair_name": DictElement(
                required=True,
                parameter_form=_required_string(
                    "Pair name",
                    "Transit switch pair",
                    "Displayed in the pair-status service and port-service details.",
                ),
            ),
            "host_a": DictElement(
                required=True,
                parameter_form=_required_string(
                    "Switch A Checkmk host name",
                    "041-Transit-001",
                ),
            ),
            "host_b": DictElement(
                required=True,
                parameter_form=_required_string(
                    "Switch B Checkmk host name",
                    "041-Transit-002",
                ),
            ),
            "service_regex": DictElement(
                required=True,
                parameter_form=_required_string(
                    "Interface service description regular expression",
                    r"^Interface (?P<item>.+)$",
                    "Must capture the one-to-one port key in a named group called 'item' "
                    "or in the first capture group. The default matches Checkmk's standard "
                    "service descriptions, for example 'Interface 01' or 'Interface Gi0/1'.",
                ),
            ),
        },
    )


rule_spec_switch_port_sync = SpecialAgent(
    topic=Topic.NETWORKING,
    name="switch_port_sync",
    title=Title("Switch port synchronization"),
    parameter_form=_parameter_form,
)
