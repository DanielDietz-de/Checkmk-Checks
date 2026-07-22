#!/usr/bin/env python3
"""Notification parameters for the Ivanti/Cherwell integration."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import NotificationParameters, Topic


def _required_string(title: str, help_text: str) -> String:
    return String(
        title=Title(title),
        help_text=Help(help_text),
        custom_validate=(LengthInRange(min_value=1),),
    )


def _parameters_cherwell_notify() -> Dictionary:
    return Dictionary(
        title=Title("Create Ivanti/Cherwell notification"),
        help_text=Help(
            "All API connections require verified HTTPS. Tenant-specific "
            "business-object and field identifiers are configured in the rule."
        ),
        elements={
            "api_url": DictElement(
                parameter_form=_required_string(
                    "Incident API URL",
                    "Absolute HTTPS URL of the Cherwell business-object endpoint.",
                ),
                required=True,
            ),
            "token_url": DictElement(
                parameter_form=_required_string(
                    "Token API URL",
                    "Absolute HTTPS URL of the OAuth token endpoint.",
                ),
                required=True,
            ),
            "client_id": DictElement(
                parameter_form=_required_string(
                    "Client ID", "OAuth client ID for authentication."
                ),
                required=True,
            ),
            "username": DictElement(
                parameter_form=_required_string(
                    "Username", "Cherwell API username."
                ),
                required=True,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Authentication password"),
                    help_text=Help("Password for the Cherwell API user."),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "business_object_id": DictElement(
                parameter_form=_required_string(
                    "Business object ID",
                    "Cherwell busObId for incidents in this tenant.",
                ),
                required=True,
            ),
            "description_field_id": DictElement(
                parameter_form=_required_string(
                    "Description field ID",
                    "Field ID receiving the generated Checkmk description.",
                ),
                required=True,
            ),
            "insert_fields_json": DictElement(
                parameter_form=String(
                    title=Title("Additional insert fields"),
                    help_text=Help(
                        "JSON list of objects with fieldId, value, and optional "
                        "dirty. Example: [{\"fieldId\":\"...\",\"value\":\"Checkmk\"}]"
                    ),
                    prefill=DefaultValue("[]"),
                ),
                required=True,
            ),
            "update_fields_json": DictElement(
                parameter_form=String(
                    title=Title("Post-create update fields"),
                    help_text=Help(
                        "JSON list of fields to update after incident creation. "
                        "Leave as [] to skip the second API request."
                    ),
                    prefill=DefaultValue("[]"),
                ),
                required=True,
            ),
            "cache_scope": DictElement(
                parameter_form=String(
                    title=Title("Cache scope"),
                    help_text=Help("Cherwell cacheScope value."),
                    prefill=DefaultValue("Tenant"),
                ),
                required=True,
            ),
            "recovery_mode": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Recovery handling"),
                    elements=(
                        SingleChoiceElement(
                            name="ignore",
                            title=Title("Ignore recovery notifications"),
                        ),
                        SingleChoiceElement(
                            name="create",
                            title=Title("Create a separate recovery incident"),
                        ),
                    ),
                    prefill=DefaultValue("ignore"),
                ),
                required=True,
            ),
            "ca_bundle": DictElement(
                parameter_form=String(
                    title=Title("Cherwell CA bundle"),
                    help_text=Help(
                        "Optional absolute path to a private CA bundle. "
                        "Leave empty to use the system trust store."
                    ),
                ),
                required=False,
            ),
            "timeout": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Request timeout"),
                    displayed_magnitudes=(TimeMagnitude.SECOND,),
                    prefill=DefaultValue(10.0),
                ),
                required=True,
            ),
            "automation_secret": DictElement(
                parameter_form=Password(
                    title=Title("Checkmk automation secret"),
                    help_text=Help(
                        "Used only to acknowledge Event Console problems."
                    ),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "cmk_server": DictElement(
                parameter_form=_required_string(
                    "Checkmk server",
                    "Hostname with optional port; no URL scheme or path.",
                ),
                required=True,
            ),
            "cmk_site": DictElement(
                parameter_form=_required_string(
                    "Checkmk site", "Checkmk site name."
                ),
                required=True,
            ),
            "cmk_ca_bundle": DictElement(
                parameter_form=String(
                    title=Title("Checkmk CA bundle"),
                    help_text=Help(
                        "Optional absolute path to a private CA bundle. "
                        "Leave empty to use the system trust store."
                    ),
                ),
                required=False,
            ),
        },
    )


rule_spec_cherwell_notify = NotificationParameters(
    title=Title("Cherwell notify"),
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_parameters_cherwell_notify,
    name="cherwell_notify",
)
