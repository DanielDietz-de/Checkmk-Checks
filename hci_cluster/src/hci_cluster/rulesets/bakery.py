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

_LEGACY_FILTER_TYPES = {
    "None": "none",
    "Inclusion": "inclusion",
    "Exclusion": "exclusion",
}


def _migrate_deployment_parameters(raw_value: object) -> dict[str, object]:
    """Handle migrate deployment parameters for this module's workflow."""
    if not isinstance(raw_value, dict):
        raise TypeError("HCI Cluster deployment parameters must be a dictionary")
    migrated = dict(raw_value)
    filter_type = migrated.get("filter_type")
    if isinstance(filter_type, str):
        migrated["filter_type"] = _LEGACY_FILTER_TYPES.get(filter_type, filter_type)
    return migrated


def _deployment_parameters() -> Dictionary:
    """Handle deployment parameters for this module's workflow."""
    return Dictionary(
        title=Title("Deploy HCI Cluster plug-in"),
        migrate=_migrate_deployment_parameters,
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
                    help_text=Help(
                        "Choose whether the filter pattern includes or excludes matches."
                    ),
                    elements=(
                        SingleChoiceElement(name="none", title=Title("No filter")),
                        SingleChoiceElement(
                            name="inclusion", title=Title("Inclusion filter")
                        ),
                        SingleChoiceElement(
                            name="exclusion", title=Title("Exclusion filter")
                        ),
                    ),
                    prefill=DefaultValue("none"),
                ),
            ),
            "filter_pattern": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Filter pattern"),
                    help_text=Help(
                        "Optional cluster resource filter, for example HCI."
                    ),
                ),
            ),
        },
    )


def _parameter_form_hci_cluster() -> Dictionary:
    """Handle parameter form hci cluster for this module's workflow."""
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
