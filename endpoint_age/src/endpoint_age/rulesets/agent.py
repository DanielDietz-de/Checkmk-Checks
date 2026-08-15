"""Setup ruleset definitions for the endpoint_age integration: agent."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Float,
    List,
    String,
)
from cmk.rulesets.v1.form_specs.validators import (
    LengthInRange,
    NumberInRange,
    Url,
    UrlProtocol,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _source_form():
    """Handle source form for this module's workflow."""
    return CascadingSingleChoice(
        title=Title("Where to read the age from"),
        elements=(
            CascadingSingleChoiceElement(
                name="age_header",
                title=Title("HTTP response header 'Age' (seconds)"),
                parameter_form=FixedValue(value=None),
            ),
            CascadingSingleChoiceElement(
                name="date_header",
                title=Title("HTTP response header containing a date"),
                parameter_form=String(
                    title=Title("Header name"),
                    prefill=DefaultValue("Last-Modified"),
                    custom_validate=(LengthInRange(min_value=1, max_value=128),),
                ),
            ),
            CascadingSingleChoiceElement(
                name="json_path",
                title=Title("JSON body field (dotted path)"),
                parameter_form=String(
                    title=Title("Dotted path"),
                    help_text=Help("Use list indexes such as items[0].updated_at."),
                    custom_validate=(LengthInRange(min_value=1, max_value=512),),
                ),
            ),
        ),
        prefill=DefaultValue("age_header"),
    )


def _endpoint_form():
    """Handle endpoint form for this module's workflow."""
    return Dictionary(
        help_text=Help(
            "Only public HTTPS endpoints are accepted. URLs resolving to "
            "loopback, private, link-local, reserved or multicast addresses "
            "are rejected. Custom request headers are not supported."
        ),
        elements={
            "name": DictElement(
                parameter_form=String(
                    title=Title("Service name"),
                    custom_validate=(LengthInRange(min_value=1, max_value=256),),
                ),
                required=True,
            ),
            "url": DictElement(
                parameter_form=String(
                    title=Title("Public HTTPS URL"),
                    custom_validate=(
                        LengthInRange(min_value=1, max_value=2048),
                        Url(protocols=[UrlProtocol.HTTPS]),
                    ),
                ),
                required=True,
            ),
            "source": DictElement(parameter_form=_source_form(), required=True),
            "timeout": DictElement(
                parameter_form=Float(
                    title=Title("HTTPS timeout"),
                    unit_symbol="s",
                    prefill=DefaultValue(15.0),
                    custom_validate=(
                        NumberInRange(min_value=0.5, max_value=60.0),
                    ),
                ),
                required=False,
            ),
        },
    )


def _form_special_agent_endpoint_age():
    """Handle form special agent endpoint age for this module's workflow."""
    return Dictionary(
        title=Title("Endpoint age (public HTTPS freshness)"),
        help_text=Help(
            "Monitor public HTTPS content freshness without granting the "
            "delegated Setup rule access to internal network resources."
        ),
        elements={
            "endpoints": DictElement(
                parameter_form=List(
                    title=Title("Endpoints"),
                    element_template=_endpoint_form(),
                    custom_validate=(LengthInRange(min_value=1, max_value=100),),
                ),
                required=True,
            ),
        },
    )


rule_spec_endpoint_age = SpecialAgent(
    name="endpoint_age",
    topic=Topic.GENERAL,
    parameter_form=_form_special_agent_endpoint_age,
    title=Title("Endpoint age (public HTTPS freshness)"),
)
