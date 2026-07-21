from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Password,
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


def _form_spec_bhome() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Sends Checkmk events to BMC Helix Operations Management by using "
            "the tenant API key directly. Event creation is attempted once to "
            "avoid duplicates after ambiguous timeouts."
        ),
        elements={
            "portal_domain": DictElement(
                parameter_form=_required_string(
                    "BMC Helix portal domain",
                    "Portal hostname with optional port, without https:// or a path.",
                ),
                required=True,
            ),
            "id": DictElement(
                parameter_form=_required_string(
                    "Tenant ID",
                    "Tenant ID from the BMC Helix API key.",
                ),
                required=True,
            ),
            "access": DictElement(
                parameter_form=Password(
                    title=Title("Access key"),
                    help_text=Help("Access-key component of the tenant API key."),
                ),
                required=True,
            ),
            "secret": DictElement(
                parameter_form=Password(
                    title=Title("Secret key"),
                    help_text=Help("Secret-key component of the tenant API key."),
                ),
                required=True,
            ),
            "timeout": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Request timeout"),
                    displayed_magnitudes=(TimeMagnitude.SECOND,),
                    prefill=DefaultValue(10.0),
                ),
                required=True,
            ),
            "ca_bundle": DictElement(
                parameter_form=String(
                    title=Title("Private CA bundle"),
                    help_text=Help(
                        "Optional absolute path to a regular CA bundle file. "
                        "Leave empty to use the system trust store."
                    ),
                ),
                required=False,
            ),
        },
    )


rule_spec_bhome_notify = NotificationParameters(
    name="bhome_notify",
    title=Title("BMC Helix Events API"),
    topic=Topic.NOTIFICATIONS,
    parameter_form=_form_spec_bhome,
)
