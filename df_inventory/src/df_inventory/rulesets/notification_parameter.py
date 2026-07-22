#!/usr/bin/env python3
"""Notification parameters for filesystem-owner mail delivery."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import NotificationParameters, Topic


def _parameter_form_df_mail() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Uses the standard Checkmk mail notification settings. Before sending, "
            "the notification program replaces the recipient with the filesystem "
            "owner address stored in the host inventory when one is available."
        ),
        elements={},
    )


rule_spec_df_mail = NotificationParameters(
    name="df_mail",
    title=Title("Filesystem owner mail"),
    topic=Topic.NOTIFICATIONS,
    parameter_form=_parameter_form_df_mail,
)
