#!/usr/bin/env python3
"""
UCP / MKE Health Special Agent Ruleset

Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""
from cmk.rulesets.v1 import Title, Help, Label
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    Dictionary,
    DictElement,
    Integer,
    List,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NumberInRange
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _node_form():
    return Dictionary(
        title=Title("Node"),
        elements={
            "name": DictElement(
                parameter_form=String(
                    title=Title("Host name"),
                    help_text=Help(
                        "Name of the node. When piggyback is enabled the per-node "
                        "check is distributed to the Checkmk host of this name "
                        "(e.g. lx1-dockucp1)."
                    ),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "url": DictElement(
                parameter_form=String(
                    title=Title("_ping URL"),
                    help_text=Help(
                        "Full URL of the MKE manager _ping endpoint "
                        "(e.g. https://lx1-dockucp1/_ping). HTTP 200 is considered "
                        "healthy, any other status code unhealthy."
                    ),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
        },
    )


def _valuespec_special_agent_ucp_health():
    return Dictionary(
        title=Title("UCP / MKE Health Monitoring"),
        help_text=Help(
            "This rule activates a special agent that queries the Mirantis "
            "Kubernetes Engine (MKE / UCP) manager _ping endpoint of one or more "
            "nodes. Each node yields a 'UCP Healthy' local check; an optional "
            "collection check aggregates the nodes on the configured host."
        ),
        elements={
            "nodes": DictElement(
                parameter_form=List(
                    title=Title("Nodes"),
                    help_text=Help("The MKE manager nodes to query."),
                    element_template=_node_form(),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "service_name": DictElement(
                parameter_form=String(
                    title=Title("Per-node service name"),
                    help_text=Help(
                        "Service description for the per-node health check. With "
                        "piggyback enabled every node host gets one service of this "
                        "name; without piggyback the node name is appended to keep "
                        "the descriptions unique."
                    ),
                    prefill=DefaultValue("UCP Healthy"),
                ),
                required=False,
            ),
            "piggyback": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Distribute per-node checks as piggyback data"),
                    label=Label("Send each node's check to the node host via piggyback"),
                    help_text=Help(
                        "When enabled, each node's 'UCP Healthy' check is wrapped in "
                        "a piggyback section so it appears on the Checkmk host with "
                        "the node name. When disabled, all node checks stay on the "
                        "host this special agent is configured on."
                    ),
                ),
                required=False,
            ),
            "collection": DictElement(
                parameter_form=Dictionary(
                    title=Title("Collection check"),
                    help_text=Help(
                        "Aggregate all nodes into one check that stays on the host "
                        "this special agent is configured on. Leave unset to only "
                        "emit the per-node checks (e.g. for the develop environment)."
                    ),
                    elements={
                        "service_name": DictElement(
                            parameter_form=String(
                                title=Title("Collection service name"),
                                prefill=DefaultValue("UCP Manager"),
                            ),
                            required=False,
                        ),
                        "warn_unhealthy": DictElement(
                            parameter_form=Integer(
                                title=Title("WARN at unhealthy nodes"),
                                help_text=Help(
                                    "Collection check goes WARN once this many nodes "
                                    "are unhealthy. Leave unset to skip the WARN level."
                                ),
                                custom_validate=(NumberInRange(min_value=1),),
                            ),
                            required=False,
                        ),
                        "crit_unhealthy": DictElement(
                            parameter_form=Integer(
                                title=Title("CRIT at unhealthy nodes"),
                                help_text=Help(
                                    "Collection check goes CRIT once this many nodes "
                                    "are unhealthy."
                                ),
                                prefill=DefaultValue(2),
                                custom_validate=(NumberInRange(min_value=1),),
                            ),
                            required=True,
                        ),
                    },
                ),
                required=False,
            ),
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Title("HTTP timeout (seconds)"),
                    prefill=DefaultValue(10),
                    custom_validate=(NumberInRange(min_value=1),),
                ),
                required=False,
            ),
            "no_verify_ssl": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Ignore TLS certificate"),
                    label=Label("Do not verify the TLS certificate of the _ping endpoint"),
                    help_text=Help(
                        "The _ping endpoints often present a certificate that does "
                        "not yet cover the requested SNI, so verification is disabled "
                        "by default (only the HTTP status code is evaluated). When "
                        "disabled, the server certificate is verified against the "
                        "Checkmk server's system trust store (add the internal CA "
                        "there, or set REQUESTS_CA_BUNDLE) - no CA path needed here."
                    ),
                    prefill=DefaultValue(True),
                ),
                required=False,
            ),
            "client_cert": DictElement(
                parameter_form=String(
                    title=Title("Client certificate (PEM)"),
                    help_text=Help(
                        "Optional. Path (on the Checkmk server) to the administrator "
                        "client certificate in PEM format. Presenting it as a TLS "
                        "client certificate makes the _ping endpoint return a detailed "
                        "message for unhealthy components, which is then shown in the "
                        "check output. May contain the private key as well, otherwise "
                        "provide the key file separately below."
                    ),
                ),
                required=False,
            ),
            "client_key": DictElement(
                parameter_form=String(
                    title=Title("Client key file (PEM)"),
                    help_text=Help(
                        "Optional. Path (on the Checkmk server) to the private key of "
                        "the client certificate, if it is not already contained in the "
                        "certificate file above. Protect it with owner-only permissions."
                    ),
                ),
                required=False,
            ),
        },
    )


rule_spec_ucp_health = SpecialAgent(
    name="ucp_health",
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_special_agent_ucp_health,
    title=Title("UCP / MKE Health Monitoring"),
)
