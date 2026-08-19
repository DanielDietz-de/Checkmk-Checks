#!/usr/bin/env python3
"""Setup ruleset definitions for the cisco_catalyst_9k_vss_switch_redundancy_state integration: cisco catalyst 9k vss switch redundancy state."""


from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_cisco_catalyst_9k_vss_switch_redundancy_state() -> Dictionary:
    """Handle parameter form cisco catalyst 9k vss switch redundancy state for this module's workflow."""
    return Dictionary(
        elements={
            "switch_role": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Expected switch role"),
                    elements=[
                        SingleChoiceElement(name="role_1", title=Title("master")),
                        SingleChoiceElement(name="role_2", title=Title("member")),
                        SingleChoiceElement(name="role_3", title=Title("not member")),
                        SingleChoiceElement(name="role_4", title=Title("standby")),
                    ],
                ),
            ),
        },
    )


rule_spec_cisco_catalyst_9k_vss_switch_redundancy_state = CheckParameters(
    name="cisco_catalyst_9k_vss_switch_redundancy_state",
    title=Title("Cisco Catalyst 9k redundancy State"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form_cisco_catalyst_9k_vss_switch_redundancy_state,
    condition=HostAndItemCondition(item_title=Title("Switch number")),
)
