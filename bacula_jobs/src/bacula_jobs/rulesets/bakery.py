#!/usr/bin/env python3
"""Agent Bakery rule for the Bacula/Bareos jobs collector."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NumberInRange
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic

_DEPLOYMENT_MODES = {"sync", "cached", "do_not_deploy"}


def _migrate_deployment(value: Any) -> tuple[str, Any]:
    """Translate both current choices and historical Bakery sentinels safely."""

    if value is None:
        return "do_not_deploy", None
    if isinstance(value, Mapping):
        # The legacy dropdown represented "deploy" as an empty dictionary.
        return "sync", None
    if isinstance(value, (tuple, list)) and value:
        mode = str(value[0])
        if mode in _DEPLOYMENT_MODES:
            interval = value[1] if len(value) > 1 else None
            return mode, interval
        return "do_not_deploy", None
    if isinstance(value, str) and value in _DEPLOYMENT_MODES:
        return value, None
    return "do_not_deploy", None


def _migrate(value: Any) -> dict[str, Any] | Any:
    """Handle migrate for this module's workflow."""
    if isinstance(value, Mapping) and "settings" in value:
        migrated = dict(value)
        migrated["deployment"] = _migrate_deployment(
            migrated.get("deployment", ("cached", 300.0))
        )
        return migrated
    if isinstance(value, (tuple, list)) and len(value) >= 2:
        deployment = _migrate_deployment(value[0])
        old = value[1] if isinstance(value[1], Mapping) else {}
        settings = {
            "backend": "postgresql"
            if old.get("backend_type") in {"pgsql", "postgresql"}
            else "mysql",
            "database": old.get("dbname", "bacula"),
            "user": old.get("dbuser", "bacula"),
            "host": old.get("dbhost", "localhost"),
            "port": 5432
            if old.get("backend_type") in {"pgsql", "postgresql"}
            else 3306,
            "timeout": 15,
        }
        return {"deployment": deployment, "settings": settings}
    return value


def _settings_form() -> Dictionary:
    """Handle settings form for this module's workflow."""
    return Dictionary(
        title=Title("Database connection"),
        help_text=Help(
            "Passwords are not stored in this rule. Reference an existing "
            "0600 client credential file on the monitored host."
        ),
        elements={
            "backend": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Database backend"),
                    elements=(
                        SingleChoiceElement(name="mysql", title=Title("MySQL / MariaDB")),
                        SingleChoiceElement(name="postgresql", title=Title("PostgreSQL")),
                    ),
                    prefill=DefaultValue("mysql"),
                ),
                required=True,
            ),
            "database": DictElement(
                parameter_form=String(
                    title=Title("Database name"),
                    prefill=DefaultValue("bacula"),
                    custom_validate=(LengthInRange(min_value=1, max_value=128),),
                ),
                required=True,
            ),
            "user": DictElement(
                parameter_form=String(
                    title=Title("Database user"),
                    prefill=DefaultValue("bacula"),
                    custom_validate=(LengthInRange(min_value=1, max_value=128),),
                ),
                required=True,
            ),
            "host": DictElement(
                parameter_form=String(
                    title=Title("Database host"),
                    prefill=DefaultValue("localhost"),
                    custom_validate=(LengthInRange(min_value=1, max_value=255),),
                ),
                required=True,
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("Database port"),
                    prefill=DefaultValue(3306),
                    custom_validate=(NumberInRange(min_value=1, max_value=65535),),
                ),
                required=True,
            ),
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Title("Database timeout"),
                    unit_symbol="s",
                    prefill=DefaultValue(15),
                    custom_validate=(NumberInRange(min_value=1, max_value=120),),
                ),
                required=True,
            ),
            "mysql_defaults_file": DictElement(
                parameter_form=String(
                    title=Title("MySQL defaults file"),
                    help_text=Help(
                        "Optional absolute path to a root-owned or otherwise "
                        "protected 0600 file containing MySQL client credentials."
                    ),
                ),
                required=False,
            ),
            "postgres_passfile": DictElement(
                parameter_form=String(
                    title=Title("PostgreSQL password file"),
                    help_text=Help(
                        "Optional absolute path to a protected 0600 pgpass file."
                    ),
                ),
                required=False,
            ),
            "postgres_os_user": DictElement(
                parameter_form=String(
                    title=Title("PostgreSQL operating-system user"),
                    help_text=Help(
                        "Optional local account used through runuser for peer "
                        "authentication. No shell is invoked."
                    ),
                ),
                required=False,
            ),
        },
    )


def _agent_config_bacula_jobs() -> Dictionary:
    """Handle agent config bacula jobs for this module's workflow."""
    return Dictionary(
        title=Title("Bacula/Bareos jobs collector"),
        migrate=_migrate,
        elements={
            "deployment": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy and run synchronously"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="cached",
                            title=Title("Deploy and run asynchronously"),
                            parameter_form=TimeSpan(
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(300.0),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("cached"),
                ),
                required=True,
            ),
            "settings": DictElement(
                parameter_form=_settings_form(),
                required=True,
            ),
        },
    )


rule_spec_bacula_jobs_agent = AgentConfig(
    # Keep the historical identifier so existing agent_config:bacula rules are
    # loaded and passed through the migration function during upgrades.
    name="bacula",
    title=Title("Bacula/Bareos jobs collector"),
    topic=Topic.APPLICATIONS,
    parameter_form=_agent_config_bacula_jobs,
)
