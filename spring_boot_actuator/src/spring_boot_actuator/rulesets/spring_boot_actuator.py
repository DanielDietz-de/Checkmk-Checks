#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from cmk.rulesets.v1 import Title, Help, Label
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    Dictionary,
    DictElement,
    List,
    Password,
    ServiceState,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostAndItemCondition,
    SpecialAgent,
    Topic,
)


def _parameter_form_special_agent():
    return Dictionary(
        title=Title("Spring Boot Actuator"),
        help_text=Help(
            "Query a Spring Boot Actuator health endpoint (usually "
            "'/actuator/health') and monitor every reported health "
            "component as its own service."
        ),
        elements={
            "url": DictElement(
                parameter_form=String(
                    title=Title("Health endpoint URL"),
                    help_text=Help(
                        "Full URL of the actuator health endpoint, e.g. "
                        "'https://app.example.com/actuator/health'. The "
                        "endpoint must expose per-component details "
                        "('management.endpoint.health.show-details: always')."
                    ),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "username": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help("Optional HTTP basic auth username."),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=False,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Password"),
                ),
                required=False,
            ),
            "verify_ssl": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Verify TLS certificate"),
                    label=Label("Verify the servers TLS certificate"),
                    prefill=DefaultValue(True),
                ),
                required=False,
            ),
        },
    )


rule_spec_spring_boot_actuator = SpecialAgent(
    name="spring_boot_actuator",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_special_agent,
    title=Title("Spring Boot Actuator"),
)


def _parameter_form_check():
    return Dictionary(
        title=Title("Spring Boot Actuator health"),
        help_text=Help(
            "Override how the actuator status strings (UP, DOWN, "
            "OUT_OF_SERVICE, UNKNOWN, ...) of a health component are mapped "
            "to a monitoring state. Unmapped statuses keep their built-in "
            "default (UP is OK, OUT_OF_SERVICE is WARN, DOWN is CRIT, "
            "everything else UNKNOWN)."
        ),
        elements={
            "status_map": DictElement(
                parameter_form=List(
                    title=Title("Map actuator status to monitoring state"),
                    element_template=Dictionary(
                        elements={
                            "status": DictElement(
                                parameter_form=String(
                                    title=Title("Actuator status"),
                                    help_text=Help(
                                        "Status string as reported by the "
                                        "actuator, e.g. 'DOWN'. Matched "
                                        "case-insensitively."
                                    ),
                                    custom_validate=(LengthInRange(min_value=1),),
                                ),
                                required=True,
                            ),
                            "state": DictElement(
                                parameter_form=ServiceState(
                                    title=Title("Monitoring state"),
                                    prefill=DefaultValue(ServiceState.CRIT),
                                ),
                                required=True,
                            ),
                        },
                    ),
                ),
                required=False,
            ),
        },
    )


rule_spec_spring_boot_actuator_check = CheckParameters(
    name="spring_boot_actuator",
    title=Title("Spring Boot Actuator health"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_check,
    condition=HostAndItemCondition(item_title=Title("Health component")),
)
