#!/usr/bin/env python3

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, String, validators
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _required_string(title: str, help_text: str | None = None) -> String:
    return String(
        title=Title(title),
        help_text=Help(help_text) if help_text else None,
        custom_validate=(validators.LengthInRange(min_value=1),),
    )


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Switch port synchronization"),
        help_text=Help(
            "Compares already monitored Checkmk interface services on two switches. "
            "Apply one explicitly configured rule to both switch hosts. No values are "
            "prefilled and no additional SNMP polling is performed. At discovery, a port "
            "pair is selected when at least one member is confirmed up; ports down on both "
            "members are treated as unused."
        ),
        elements={
            "pair_name": DictElement(
                required=True,
                parameter_form=_required_string(
                    "Pair name",
                    "Required descriptive name shown in the pair-status service and "
                    "port-service details, for example 'Switch pair 1'.",
                ),
            ),
            "host_a": DictElement(
                required=True,
                parameter_form=_required_string(
                    "Switch 1 Checkmk host name",
                    "Required exact Checkmk host name of the first switch, for example "
                    "'switch-1'.",
                ),
            ),
            "host_b": DictElement(
                required=True,
                parameter_form=_required_string(
                    "Switch 2 Checkmk host name",
                    "Required exact Checkmk host name of the second switch, for example "
                    "'switch-2'.",
                ),
            ),
            "service_regex": DictElement(
                required=True,
                parameter_form=_required_string(
                    "Interface service description regular expression",
                    "Required expression that captures the one-to-one port key in a named "
                    "group called 'item' or in the first capture group. A common explicit "
                    "value for standard Checkmk service descriptions is "
                    "'^Interface (?P<item>.+)$'.",
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
