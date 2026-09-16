#!/usr/bin/env python3
"""Setup rule for the Synology Active Backup for Microsoft 365 special agent."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, Password, String, migrate_to_password
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Synology Active Backup for Microsoft 365"),
        help_text=Help(
            "Retrieves the token-protected JSON status endpoint exposed by the Synology "
            "Active Backup collector package. The initial framework uses the collector's "
            "HTTP API and therefore requires strict network filtering to the NAS."
        ),
        elements={
            "api_host": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Collector host name or IP address"),
                    help_text=Help("Synology NAS address reachable from the Checkmk site."),
                ),
            ),
            "api_port": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Collector API port"),
                    help_text=Help("Default upstream API port is 9876."),
                    prefill=DefaultValue("9876"),
                ),
            ),
            "api_token": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Collector API token"),
                    help_text=Help(
                        "Use the Checkmk Password Store. Checkmk passes only a secret reference "
                        "to the special agent on Checkmk 2.5."
                    ),
                    migrate=migrate_to_password,
                ),
            ),
            "timeout": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Request timeout in seconds"),
                    prefill=DefaultValue("10"),
                ),
            ),
        },
    )


rule_spec_synology_active_backup_m365 = SpecialAgent(
    topic=Topic.GENERAL,
    name="synology_active_backup_m365",
    title=Title("Synology Active Backup for Microsoft 365"),
    parameter_form=_parameter_form,
)
