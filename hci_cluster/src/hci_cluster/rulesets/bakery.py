#!/usr/bin/env python3
"""Agent bakery rule for HCI cluster monitoring."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _deployment_parameters() -> Dictionary:
    return Dictionary(
        title=Title("Deploy HCI Cluster plug-in"),
        elements={
            "domain": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Domain"),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
            ),
            "filter_type": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Filter type"),
                    help_text=Help("Choose whether the filter pattern includes or excludes matches."),
                    elements=(
                        SingleChoiceElement(name="None", title=Title("No filter")),
                        SingleChoiceElement(name="Inclusion", title=Title("Inclusion filter")),
                        SingleChoiceElement(name="Exclusion", title=Title("Exclusion filter")),
                    ),
                    prefill=DefaultValue("None"),
                ),
            ),
            "filter_pattern": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Filter pattern"),
                    help_text=Help("Optional cluster resource filter, for example HCI."),
                ),
            ),
        },
    )


def _parameter_form_hci_cluster() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Deploys the Windows HCI Cluster agent plug-in for monitoring cluster "
            "nodes, resources, storage pools, virtual disks, volumes, and jobs."
        ),
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="deploy",
                            title=Title("Deploy the plug-in"),
                            parameter_form=_deployment_parameters(),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("deploy"),
                ),
            ),
        },
    )


rule_spec_hci_cluster = AgentConfig(
    name="hci_cluster",
    title=Title("HCI Cluster Monitoring (Windows)"),
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_parameter_form_hci_cluster,
)
