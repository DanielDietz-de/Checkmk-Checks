from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    MultilineText,
    Password,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import NotificationParameters, Topic


def _parameters_kentix() -> Dictionary:
    return Dictionary(
        title=Title("Kentix SMS Gateway notification"),
        help_text=Help(
            "Submits one HTTPS POST to the legacy Kentix SMS gateway. "
            "Credentials and message content are placed in the request body, "
            "not in the URL."
        ),
        elements={
            "ipaddress": DictElement(
                parameter_form=String(
                    title=Title("Kentix gateway host"),
                    help_text=Help(
                        "HTTPS hostname with optional port. An https:// prefix "
                        "is accepted; paths, queries and credentials are rejected."
                    ),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "password": DictElement(
                parameter_form=Password(title=Title("SMS gateway password")),
                required=True,
            ),
            "template_text": DictElement(
                parameter_form=MultilineText(title=Title("Message content")),
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
                        "Optional absolute path to a regular CA bundle. "
                        "Leave empty to use the system trust store."
                    ),
                ),
                required=False,
            ),
        },
    )


rule_spec_kentix = NotificationParameters(
    title=Title("Kentix SMS Gateway notification"),
    topic=Topic.NOTIFICATIONS,
    parameter_form=_parameters_kentix,
    name="kentix",
)
