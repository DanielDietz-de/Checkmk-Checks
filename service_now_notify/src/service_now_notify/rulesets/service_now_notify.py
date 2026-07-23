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


def _parameters_service_now_notify() -> Dictionary:
    return Dictionary(
        title=Title("ServiceNow notification"),
        help_text=Help(
            "Create and close incidents through a fixed HTTPS gateway. "
            "Credential-bearing requests are never retried automatically."
        ),
        elements={
            "api_url": DictElement(
                parameter_form=String(
                    title=Title("HTTPS API base URL"),
                    help_text=Help(
                        "Absolute HTTPS base URL. The notification appends "
                        "checkmk/incident/create or checkmk/incident/close."
                    ),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "api_user": DictElement(
                parameter_form=String(
                    title=Title("Authentication user"),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "api_password": DictElement(
                parameter_form=Password(title=Title("Authentication password")),
                required=True,
            ),
            "timeout": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Request timeout"),
                    displayed_magnitudes=(TimeMagnitude.SECOND,),
                    prefill=DefaultValue(15.0),
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
            "proxy": DictElement(
                parameter_form=String(
                    title=Title("HTTPS proxy"),
                    help_text=Help(
                        "Optional absolute HTTPS proxy URL without embedded credentials."
                    ),
                ),
                required=False,
            ),
        },
    )


rule_spec_service_now_notify = NotificationParameters(
    title=Title("ServiceNow notification"),
    topic=Topic.NOTIFICATIONS,
    parameter_form=_parameters_service_now_notify,
    name="service_now_notify",
)
