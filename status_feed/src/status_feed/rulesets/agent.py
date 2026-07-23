from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, Float, List, String
from cmk.rulesets.v1.form_specs.validators import LengthInRange, Url, UrlProtocol
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _feed_form():
    return Dictionary(
        help_text=Help(
            "Only public HTTPS feeds are accepted. Internal, loopback, "
            "link-local and reserved destinations are rejected."
        ),
        elements={
            "name": DictElement(
                parameter_form=String(
                    title=Title("Feed name"),
                    custom_validate=(LengthInRange(min_value=1, max_value=256),),
                ),
                required=True,
            ),
            "url": DictElement(
                parameter_form=String(
                    title=Title("Public HTTPS feed URL"),
                    custom_validate=(Url(protocols=[UrlProtocol.HTTPS]),),
                ),
                required=True,
            ),
        },
    )


def _form_special_agent_status_feed():
    return Dictionary(
        title=Title("Public status RSS/Atom feeds"),
        help_text=Help(
            "Fetch public status feeds with direct verified HTTPS. Redirects, "
            "environment proxies and rule-configured proxies are not used."
        ),
        elements={
            "feeds": DictElement(
                parameter_form=List(
                    title=Title("Feeds"),
                    element_template=_feed_form(),
                    custom_validate=(LengthInRange(min_value=1, max_value=100),),
                ),
                required=True,
            ),
            "timeout": DictElement(
                parameter_form=Float(
                    title=Title("HTTPS timeout"),
                    unit_symbol="s",
                    prefill=DefaultValue(15.0),
                ),
                required=False,
            ),
            "user_agent": DictElement(
                parameter_form=String(
                    title=Title("User-Agent header"),
                    prefill=DefaultValue("checkmk-status-feed/2.0"),
                    custom_validate=(LengthInRange(min_value=1, max_value=256),),
                ),
                required=False,
            ),
        },
    )


rule_spec_status_feed = SpecialAgent(
    name="status_feed",
    topic=Topic.CLOUD,
    parameter_form=_form_special_agent_status_feed,
    title=Title("Public status RSS/Atom feeds"),
)
