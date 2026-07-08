#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _state_element(label, default):
    return DictElement(
        required=True,
        parameter_form=ServiceState(
            title=Title("%s") % label,
            prefill=DefaultValue(default),
        ),
    )


def _formspec_palo_alto_ha():
    return Dictionary(
        title=Title("Palo Alto HA State"),
        help_text=Help(
            "Map the reported local HA state of a Palo Alto firewall to a "
            "monitoring state. Unknown / unlisted states use the fallback."
        ),
        elements={
            "states": DictElement(
                required=True,
                parameter_form=Dictionary(
                    title=Title("Monitoring state per HA state"),
                    elements={
                        "active": _state_element(Label("active"), 0),
                        "passive": _state_element(Label("passive"), 0),
                        "active_primary": _state_element(Label("active-primary"), 0),
                        "active_secondary": _state_element(Label("active-secondary"), 0),
                        "initial": _state_element(Label("initial"), 1),
                        "tentative": _state_element(Label("tentative"), 1),
                        "suspended": _state_element(Label("suspended"), 1),
                        "non_functional": _state_element(Label("non-functional"), 2),
                        "unknown": _state_element(Label("unknown"), 1),
                        "default": _state_element(Label("Any other state"), 1),
                    },
                ),
            ),
        },
    )


rule_spec_palo_alto_ha = CheckParameters(
    name="palo_alto_ha",
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=_formspec_palo_alto_ha,
    title=Title("Palo Alto HA State"),
)
