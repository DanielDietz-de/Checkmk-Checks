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
    InputHint,
    Integer,
    LevelDirection,
    List,
    SimpleLevels,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, SpecialAgent, Topic


def _valuespec_special_agent_service_metric_counter():
    return Dictionary(
        title=Title("Service counter"),
        help_text=Help(
            "This special agent reads the local site's automation secret and therefore "
            "may only query the same Checkmk site through localhost or another loopback address."
        ),
        elements={
            "service_filters": DictElement(
                parameter_form=List(
                    title=Title("Services"),
                    help_text=Help("Service filters and metrics to aggregate."),
                    custom_validate=(LengthInRange(min_value=1),),
                    element_template=Dictionary(
                        elements={
                            "service_name": DictElement(
                                parameter_form=String(
                                    title=Title("Service name"),
                                    help_text=Help("Name of the resulting Checkmk service."),
                                    custom_validate=(LengthInRange(min_value=1),),
                                ),
                                required=True,
                            ),
                            "ls_pattern": DictElement(
                                parameter_form=String(
                                    title=Title("Livestatus filter"),
                                    help_text=Help(
                                        "Example: description~SERVICENAME;plugin_output=output. "
                                        "Use ~ for regex, = for equality, and ; to join expressions with AND."
                                    ),
                                    custom_validate=(LengthInRange(min_value=1),),
                                ),
                                required=True,
                            ),
                            "metric": DictElement(
                                parameter_form=String(
                                    title=Title("Metric to aggregate"),
                                    help_text=Help("Performance metric name from the matching services."),
                                    custom_validate=(LengthInRange(min_value=1),),
                                ),
                                required=True,
                            ),
                            "metric_label": DictElement(
                                parameter_form=String(
                                    title=Title("Metric label"),
                                    help_text=Help("Human-readable label shown in the service output."),
                                    custom_validate=(LengthInRange(min_value=1),),
                                ),
                                required=True,
                            ),
                        }
                    ),
                ),
                required=True,
            ),
            "path": DictElement(
                parameter_form=String(
                    title=Title("Local Checkmk site URL"),
                    help_text=Help(
                        "URL of this local Checkmk site using localhost or a loopback address, "
                        "for example http://localhost/cmk/. Remote hosts are rejected before "
                        "the automation secret is read."
                    ),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "timeout": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Timeout"),
                    displayed_magnitudes=[TimeMagnitude.MILLISECOND, TimeMagnitude.SECOND],
                    prefill=DefaultValue(2.5),
                ),
                required=True,
            ),
        },
    )


rule_spec_service_counter = SpecialAgent(
    name="service_metric_counter",
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_special_agent_service_metric_counter,
    title=Title("Service Metric counter"),
)


def _parameter_metric_counter() -> Dictionary:
    return Dictionary(
        elements={
            "levels": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Levels"),
                    form_spec_template=Integer(unit_symbol="Count"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                )
            ),
        }
    )


rule_spec_metric_counter = CheckParameters(
    name="service_metric_counter",
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=_parameter_metric_counter,
    title=Title("Service Metric Count"),
)
