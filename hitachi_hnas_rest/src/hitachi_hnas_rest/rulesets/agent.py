#!/usr/bin/env python3
"""
Hitachi HNAS REST API Special Agent Ruleset

Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    Password,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NetworkPort, NumberInRange
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _valuespec_special_agent_hitachi_hnas_rest():
    """
    Special Agent configuration for Hitachi HNAS
    """
    return Dictionary(
        title=Title("Hitachi HNAS via REST API"),
        help_text=Help(
            "This rule activates a special agent which monitors a Hitachi NAS "
            "(HNAS) system via its File Storage REST API (v8). It monitors "
            "filesystems, snapshots, storage pools, virtual servers (EVS), "
            "cluster nodes and system drives."
        ),
        elements={
            "address": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Address to connect to"),
                    help_text=Help(
                        "By default the host name is used, so that TLS "
                        "certificate verification works. Select the primary "
                        "IP address if the HNAS is not resolvable via DNS, "
                        "or enter a custom FQDN."
                    ),
                    prefill=DefaultValue("host_name"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="host_name",
                            title=Title("Host name"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="ip",
                            title=Title("Primary IP address of the host"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="custom",
                            title=Title("Custom address"),
                            parameter_form=String(
                                custom_validate=(LengthInRange(min_value=1),),
                            ),
                        ),
                    ],
                ),
                required=True,
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("TCP port"),
                    help_text=Help("Port of the REST API (default: 8444)"),
                    prefill=DefaultValue(8444),
                    custom_validate=(NetworkPort(),),
                ),
                required=False,
            ),
            "auth": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Authentication"),
                    help_text=Help(
                        "The API key method is recommended by Hitachi. API keys "
                        "can be created on the HNAS with the apikey-create "
                        "command. Username and password are supported for "
                        "backward compatibility."
                    ),
                    prefill=DefaultValue("api_key"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="api_key",
                            title=Title("API key"),
                            parameter_form=Dictionary(
                                elements={
                                    "key": DictElement(
                                        parameter_form=Password(
                                            title=Title("API key"),
                                            custom_validate=(LengthInRange(min_value=1),),
                                        ),
                                        required=True,
                                    ),
                                },
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="userpass",
                            title=Title("Username and password"),
                            parameter_form=Dictionary(
                                elements={
                                    "username": DictElement(
                                        parameter_form=String(
                                            title=Title("Username"),
                                            custom_validate=(LengthInRange(min_value=1),),
                                        ),
                                        required=True,
                                    ),
                                    "password": DictElement(
                                        parameter_form=Password(
                                            title=Title("Password"),
                                            custom_validate=(LengthInRange(min_value=1),),
                                        ),
                                        required=True,
                                    ),
                                },
                            ),
                        ),
                    ],
                ),
                required=True,
            ),
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Title("HTTP timeout (seconds)"),
                    prefill=DefaultValue(30),
                    custom_validate=(NumberInRange(min_value=1),),
                ),
                required=False,
            ),
            "no_cert_check": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Disable TLS certificate verification"),
                    help_text=Help(
                        "Disable the verification of the TLS certificate. "
                        "Needed for self-signed certificates."
                    ),
                ),
                required=False,
            ),
        },
    )


rule_spec_hitachi_hnas_rest = SpecialAgent(
    name="hitachi_hnas_rest",
    topic=Topic.STORAGE,
    parameter_form=_valuespec_special_agent_hitachi_hnas_rest,
    title=Title("Hitachi HNAS via REST API"),
)
