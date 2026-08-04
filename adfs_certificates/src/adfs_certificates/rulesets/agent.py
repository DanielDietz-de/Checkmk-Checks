#!/usr/bin/env python3
"""
ADFS Certificate Special Agent Ruleset

Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""
from cmk.rulesets.v1 import Title, Help
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    Dictionary,
    DictElement,
    Integer,
    String,
)
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostAndItemCondition,
    SpecialAgent,
    Topic,
)


def _valuespec_special_agent_adfs_certificates():
    return Dictionary(
        title=Title("ADFS Certificate Monitoring"),
        help_text=Help(
            "This rule activates a special agent that fetches the ADFS federation "
            "metadata XML and monitors the embedded X.509 certificates for expiry."
        ),
        elements={
            "proxy_url": DictElement(
                parameter_form=String(
                    title=Title("Proxy URL"),
                    help_text=Help(
                        "Proxy server URL for HTTP(S) requests "
                        "(e.g. http://proxy.example.com:8080)"
                    ),
                ),
                required=False,
            ),
            "no_verify_ssl": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Disable SSL verification"),
                    help_text=Help(
                        "Disable SSL certificate verification when fetching the "
                        "federation metadata (not recommended for production)"
                    ),
                ),
                required=False,
            ),
            "debug": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Enable debug output"),
                    help_text=Help(
                        "Print diagnostic information to stderr (metadata URL, "
                        "HTTP status, found and deduplicated certificates, full "
                        "tracebacks). Visible when running the agent manually or "
                        "via 'cmk --debug -d <host>'."
                    ),
                ),
                required=False,
            ),
        },
    )


rule_spec_adfs_certificates = SpecialAgent(
    name="adfs_certificates",
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_special_agent_adfs_certificates,
    title=Title("ADFS Certificate Monitoring"),
)


def _valuespec_check_adfs_certificates():
    return Dictionary(
        title=Title("ADFS Certificate Expiry Thresholds"),
        elements={
            "warn_days": DictElement(
                parameter_form=Integer(
                    title=Title("Warning threshold (days)"),
                    help_text=Help("Warn if a certificate expires within this many days"),
                    prefill=DefaultValue(30),
                ),
                required=True,
            ),
            "crit_days": DictElement(
                parameter_form=Integer(
                    title=Title("Critical threshold (days)"),
                    help_text=Help("Critical if a certificate expires within this many days"),
                    prefill=DefaultValue(14),
                ),
                required=True,
            ),
        },
    )


rule_spec_adfs_certificates_check = CheckParameters(
    name="adfs_certificates",
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_check_adfs_certificates,
    title=Title("ADFS Certificate Expiry"),
    condition=HostAndItemCondition(item_title=Title("Certificate")),
)
