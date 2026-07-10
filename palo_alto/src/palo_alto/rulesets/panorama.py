#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _formspec_palo_alto_panorama():
    return Dictionary(
        title=Title("Palo Alto Panorama Availability"),
        help_text=Help(
            "Monitoring state a Palo Alto firewall reports when it is not "
            "connected to its configured Panorama management server. A "
            'reported state of "Connected" is always treated as OK.'
        ),
        elements={
            "state_not_connected": DictElement(
                required=True,
                parameter_form=ServiceState(
                    title=Title("State when not connected"),
                    prefill=DefaultValue(2),
                ),
            ),
        },
    )


rule_spec_palo_alto_panorama = CheckParameters(
    name="palo_alto_panorama",
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=_formspec_palo_alto_panorama,
    title=Title("Palo Alto Panorama Availability"),
)
